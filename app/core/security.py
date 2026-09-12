import bcrypt
import hashlib
import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt salted hash.
    """
    password_bytes = _password_bytes(password)
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.
    """
    try:
        password_bytes = _password_bytes(plain_password)
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False


def _password_bytes(password: str) -> bytes:
    """Validate bcrypt's 72-byte input limit before hashing or checking."""
    password_bytes = password.encode("utf-8")
    if not 8 <= len(password_bytes) <= 72:
        raise ValueError("Password must be between 8 and 72 UTF-8 bytes")
    return password_bytes


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a signed JWT Access Token containing user claims and expiration timestamp.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    issued_at = datetime.now(timezone.utc)
    to_encode.update(
        {
            "exp": expire,
            "iat": issued_at,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "typ": "access",
            "jti": secrets.token_urlsafe(16),
        }
    )
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decodes and verifies a JWT Access Token signature and expiration timestamp.
    Raises PyJWT exceptions if signature is invalid or expired.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
    )


def generate_refresh_token() -> str:
    """Generate an opaque refresh token; only its hash is persisted."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Return a deterministic one-way digest for refresh-token lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
