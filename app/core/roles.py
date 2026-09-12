from enum import Enum


class UserRole(str, Enum):
    """Application roles stored as lowercase values in the database."""
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class MembershipRole(str, Enum):
    """Roles scoped to a team or project membership."""
    MANAGER = "manager"
    MEMBER = "member"