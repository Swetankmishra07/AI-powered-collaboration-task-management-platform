from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.core.roles import UserRole
from app.database.models import User
from app.dependencies.auth import get_current_user


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Build a dependency that authorizes an authenticated user by role."""
    allowed_values = {role.value for role in allowed_roles}

    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return role_dependency


require_member = require_roles(UserRole.MEMBER, UserRole.MANAGER, UserRole.ADMIN)
require_manager = require_roles(UserRole.MANAGER, UserRole.ADMIN)
require_admin = require_roles(UserRole.ADMIN)