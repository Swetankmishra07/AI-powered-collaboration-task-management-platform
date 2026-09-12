from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.dependencies.authorization import require_admin, require_manager
from app.schemas.user import RoleUpdate, UserResponse


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserResponse], summary="List users")
def list_users(
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """Managers and admins may inspect users in the current application scope."""
    return db.query(User).order_by(User.id).all()


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Change a user's role",
)
def change_user_role(
    user_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Only an authenticated admin may change a persisted user role."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )

    user.role = role_data.role.value
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user