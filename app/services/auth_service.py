from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.database.models import RefreshToken, User
from app.schemas.user import UserCreate
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse


DUMMY_PASSWORD_HASH = hash_password("DummyPassword123")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite's naive datetime values for comparisons."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class AuthService:
    """
    Business Logic Service for User Authentication & Registration.
    """

    @staticmethod
    def register_user(user_data: UserCreate, db: Session) -> User:
        """
        Registers a new user after verifying email & username uniqueness.
        Hashes password before database persistence.
        """
        # Check if email or username is already registered
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()

        if existing_user:
            if existing_user.email == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this email already exists."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this username already exists."
            )

        # Hash raw password
        hashed_pwd = hash_password(user_data.password)

        # Create SQLAlchemy ORM model
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_pwd
        )

        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
        except Exception:
            db.rollback()
            raise

        return new_user

    @staticmethod
    def authenticate_user(login_data: LoginRequest, db: Session) -> TokenResponse:
        """
        Authenticates user credentials and generates a signed JWT Access Token.
        """
        # Query user by email
        user = db.query(User).filter(User.email == login_data.email).first()

        # Generic authentication failure (protects against account enumeration)
        password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
        if not verify_password(login_data.password, password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthService._issue_token_pair(user, db)

    @staticmethod
    def refresh_tokens(token_data: RefreshTokenRequest, db: Session) -> TokenResponse:
        """Rotate a refresh token and revoke the token presented by the client."""
        token_hash = hash_refresh_token(token_data.refresh_token)
        stored_token = (
            db.query(RefreshToken)
            .with_for_update()
            .filter(RefreshToken.token_hash == token_hash)
            .first()
        )

        if stored_token is None:
            raise AuthService._refresh_exception()

        if stored_token.revoked_at is not None:
            AuthService._revoke_user_tokens(stored_token.user_id, db)
            raise AuthService._refresh_exception()

        if _as_utc(stored_token.expires_at) <= _utc_now():
            stored_token.revoked_at = _utc_now()
            db.commit()
            raise AuthService._refresh_exception()

        new_refresh_token = generate_refresh_token()
        new_refresh_hash = hash_refresh_token(new_refresh_token)
        stored_token.revoked_at = _utc_now()
        stored_token.replaced_by_hash = new_refresh_hash

        access_token = create_access_token(
            data={"sub": str(stored_token.user.id), "email": stored_token.user.email}
        )
        replacement = RefreshToken(
            token_hash=new_refresh_hash,
            user_id=stored_token.user_id,
            expires_at=_utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        try:
            db.add(replacement)
            db.commit()
        except Exception:
            db.rollback()
            raise

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def logout(token_data: RefreshTokenRequest, db: Session) -> None:
        """Revoke a refresh token; repeated logout is intentionally idempotent."""
        stored_token = db.query(RefreshToken).filter(
            RefreshToken.token_hash == hash_refresh_token(token_data.refresh_token)
        ).first()
        if stored_token is None or stored_token.revoked_at is not None:
            return

        stored_token.revoked_at = _utc_now()
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _issue_token_pair(user: User, db: Session) -> TokenResponse:
        refresh_token = generate_refresh_token()
        refresh_record = RefreshToken(
            token_hash=hash_refresh_token(refresh_token),
            user_id=user.id,
            expires_at=_utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        try:
            db.add(refresh_record)
            db.commit()
        except Exception:
            db.rollback()
            raise

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def _revoke_user_tokens(user_id: int, db: Session) -> None:
        now = _utc_now()
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        ).update({RefreshToken.revoked_at: now}, synchronize_session=False)
        db.commit()

    @staticmethod
    def _refresh_exception(detail: str = "Invalid refresh token") -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
