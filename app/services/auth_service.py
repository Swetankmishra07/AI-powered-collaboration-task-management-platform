from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.database.models import User
from app.schemas.user import UserCreate
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token


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

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user

    @staticmethod
    def authenticate_user(login_data: LoginRequest, db: Session) -> TokenResponse:
        """
        Authenticates user credentials and generates a signed JWT Access Token.
        """
        # Query user by email
        user = db.query(User).filter(User.email == login_data.email).first()

        # Generic authentication failure (protects against account enumeration)
        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate JWT Token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return TokenResponse(access_token=access_token, token_type="bearer")
