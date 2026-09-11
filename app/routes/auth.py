from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Validates user credentials, hashes password, stores user in database, and returns created user profile."
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    POST /auth/register Endpoint
    """
    return AuthService.register_user(user_data, db)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates user credentials and returns a Bearer JWT Access Token."
)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    POST /auth/login Endpoint
    """
    return AuthService.authenticate_user(login_data, db)
