import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.core.security import decode_access_token

# OAuth2PasswordBearer scheme specifies the token endpoint URL for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI Security Dependency.
    1. Extracts Bearer token from incoming request 'Authorization' header.
    2. Decodes and verifies JWT signature and expiration.
    3. Fetches authenticated User from database.
    4. Injects 'current_user' into protected route handlers.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except jwt.ExpiredSignatureError:
        raise expired_exception
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_exception

    # Query database for user
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user
