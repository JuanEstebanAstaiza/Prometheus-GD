from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from .database import get_db
from .security import verify_token
from ..models.user import User

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    # Verify token
    payload = verify_token(token, "access")
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure user is active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure user is superuser (SUPER_ADMIN role)
    """
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns user if token is valid, None otherwise
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = verify_token(token, "access")
        if not payload:
            return None

        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_active:
            return user
    except Exception as e:
        logger.warning(f"Optional auth failed: {e}")

    return None

def require_role(allowed_roles: List[str]):
    """
    Factory function to create role-based access control dependencies

    Args:
        allowed_roles: List of role names that are allowed access

    Returns:
        Dependency function
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

# Specific role dependencies
require_super_admin = require_role(["SUPER_ADMIN"])
require_admin_dep_or_super = require_role(["SUPER_ADMIN", "ADMIN_DEP"])
require_worker_or_higher = require_role(["SUPER_ADMIN", "ADMIN_DEP", "WORKER"])
require_reader_or_higher = require_role(["SUPER_ADMIN", "ADMIN_DEP", "WORKER", "READER"])

# Role hierarchy helpers
ROLE_HIERARCHY = {
    "SUPER_ADMIN": 4,
    "ADMIN_DEP": 3,
    "WORKER": 2,
    "READER": 1
}

def has_minimum_role(user_role: str, minimum_role: str) -> bool:
    """
    Check if a user role meets the minimum required role based on hierarchy

    Args:
        user_role: User's current role
        minimum_role: Minimum required role

    Returns:
        True if user has sufficient permissions, False otherwise
    """
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(minimum_role, 999)
    return user_level >= required_level

def require_minimum_role(minimum_role: str):
    """
    Factory function to create minimum role-based access control dependencies

    Args:
        minimum_role: Minimum role required (inclusive of higher roles)

    Returns:
        Dependency function
    """
    def min_role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not has_minimum_role(current_user.role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Minimum role required: {minimum_role}"
            )
        return current_user
    return min_role_checker
