from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid

from ..core.database import get_db
from ..core.auth import get_current_active_user, require_super_admin, require_admin_dep_or_super
from ..core.security import get_password_hash
from ..models.user import User
from ..models.dependency import Dependency
from ..schemas.auth import UserCreate, UserUpdate, UserResponse, UserList
from ..schemas.common import ErrorResponse, NotFoundResponse, ConflictResponse
from ..services.audit_service import audit_service

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information
    """
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user information
    """
    update_data = user_update.dict(exclude_unset=True)

    # Don't allow updating sensitive fields
    forbidden_fields = {"role", "is_active"}
    for field in forbidden_fields:
        update_data.pop(field, None)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("", response_model=UserList, responses={
    200: {"model": UserList}
})
@router.get("/", response_model=UserList, responses={
    200: {"model": UserList}
})
async def read_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[str] = Query(None, description="Filter by role"),
    dependency_id: Optional[str] = Query(None, description="Filter by dependency"),
    email: Optional[str] = Query(None, description="Filter by email (partial match)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve users with filtering based on permissions

    - Super admin: can see all users with any filters
    - Admin: can see users in their dependency (WORKER, READER roles)
    - Worker/Reader: cannot access this endpoint
    """
    # Check permissions
    if current_user.role not in ["SUPER_ADMIN", "ADMIN_DEP"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient permissions."
        )

    query = db.query(User)

    # Apply permission-based filtering
    if current_user.role == "ADMIN_DEP":
        # Admin can only see users in their dependency with WORKER/READER roles
        if current_user.dependency_id:
            query = query.filter(
                and_(
                    User.dependency_id == current_user.dependency_id,
                    User.role.in_(["WORKER", "READER"])
                )
            )
        else:
            # Admin without dependency - no users to show
            return {"items": [], "total": 0}

    # Apply user-specified filters
    if role:
        query = query.filter(User.role == role)

    if dependency_id:
        query = query.filter(User.dependency_id == dependency_id)

    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # Get total count
    total = query.count()

    # Get paginated results
    users = query.offset(skip).limit(limit).all()

    return {"items": users, "total": total}

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, responses={
    201: {"model": UserResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
})
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, responses={
    201: {"model": UserResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    409: {"model": ConflictResponse}
})
async def create_user(
    user: UserCreate,
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Create new user with role-based permissions

    - Super admin: can create any role in any dependency
    - Admin: can create only WORKER or READER roles within their dependency
    """
    # Validate role permissions
    allowed_roles = ["SUPER_ADMIN", "ADMIN_DEP", "WORKER", "READER"]

    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(allowed_roles)}"
        )

    # Check permissions based on current user role
    if current_user.role == "ADMIN_DEP":
        # Admin can only create WORKER or READER roles
        if user.role not in ["WORKER", "READER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only create WORKER or READER users."
            )

        # Admin can only create users in their own dependency
        if user.dependency_id != current_user.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only create users in your own dependency."
            )
    # Super admin can create any role in any dependency

    # Validate dependency exists if specified
    if user.dependency_id:
        dependency = db.query(Dependency).filter(Dependency.id == user.dependency_id).first()
        if not dependency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified dependency does not exist"
            )

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    # Hash password
    password_hash = get_password_hash(user.password)

    # Create user with explicit UUID
    db_user = User(
        id=str(uuid.uuid4()),
        **user.dict(exclude={"password"}),
        password_hash=password_hash
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Log audit event
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="CREATE_USER",
        target_type="USER",
        target_id=db_user.id,
        details={
            "email": db_user.email,
            "full_name": db_user.full_name,
            "role": db_user.role,
            "dependency_id": db_user.dependency_id
        }
    )

    # TODO: Send welcome email (stubbed for now)
    # send_welcome_email(db_user.email, db_user.full_name)

    return db_user

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get user by ID (superuser only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse, responses={
    200: {"model": UserResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse},
    409: {"model": ConflictResponse}
})
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Update user with role-based permissions

    - Super admin: can update any field on any user
    - Admin: can update users in their dependency (except role changes)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    update_data = user_update.dict(exclude_unset=True)

    # Check permissions
    if current_user.role == "ADMIN_DEP":
        # Admin cannot change roles
        if "role" in update_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You cannot change user roles."
            )

        # Admin can only update users in their dependency
        if user.dependency_id != current_user.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only update users in your own dependency."
            )

        # Admin can only update WORKER/READER users
        if user.role not in ["WORKER", "READER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only update WORKER and READER users."
            )

    # Validate role if being updated
    if "role" in update_data:
        allowed_roles = ["SUPER_ADMIN", "ADMIN_DEP", "WORKER", "READER"]
        if update_data["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(allowed_roles)}"
            )

    # Validate dependency exists if being updated
    if "dependency_id" in update_data and update_data["dependency_id"]:
        dependency = db.query(Dependency).filter(Dependency.id == update_data["dependency_id"]).first()
        if not dependency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified dependency does not exist"
            )

    # Check email uniqueness if being updated
    if "email" in update_data:
        existing_user = db.query(User).filter(
            and_(User.email == update_data["email"], User.id != user_id)
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )

    # Store old values for audit
    old_values = {
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "dependency_id": user.dependency_id,
        "is_active": user.is_active
    }

    # Update user
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    # Log audit event
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="UPDATE_USER",
        target_type="USER",
        target_id=user.id,
        details={
            "old_values": old_values,
            "new_values": update_data
        }
    )

    return user

@router.delete("/{user_id}", responses={
    204: {"description": "User deleted successfully"},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Soft delete user (set is_active=false) with role-based permissions

    - Super admin: can delete any user
    - Admin: can delete WORKER/READER users in their dependency
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Don't allow deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    # Check permissions
    if current_user.role == "ADMIN_DEP":
        # Admin can only delete users in their dependency
        if user.dependency_id != current_user.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only delete users in your own dependency."
            )

        # Admin can only delete WORKER/READER users
        if user.role not in ["WORKER", "READER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only delete WORKER and READER users."
            )

    # Soft delete (deactivate user)
    old_active_status = user.is_active
    user.is_active = False

    db.commit()

    return {"message": "User deactivated successfully"}

@router.options("/{user_id}/permanent")
async def options_delete_user_permanently(user_id: str):
    """
    Handle CORS preflight for permanent delete
    """
    return {}

@router.delete("/{user_id}/permanent", responses={
    204: {"description": "User permanently deleted"},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def delete_user_permanently(
    user_id: str,
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Permanently delete user (hard delete) - only for inactive users
    
    This operation is irreversible and can only be performed on inactive users.
    Before deleting, all references to the user are set to NULL.
    
    - Super admin: can permanently delete any inactive user
    - Admin: can permanently delete inactive WORKER/READER users in their dependency
    """
    from ..models.folder import Folder
    from ..models.file import File
    from ..models.backup import BackupRecord
    from ..models.refresh_tokens import RefreshToken
    from ..models.action_logs import ActionLog
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Don't allow deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    # Only allow deleting inactive users
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot permanently delete an active user. Deactivate the user first."
        )

    # Check permissions
    if current_user.role == "ADMIN_DEP":
        # Admin can only delete users in their dependency
        if user.dependency_id != current_user.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only delete users in your own dependency."
            )

        # Admin can only delete WORKER/READER users
        if user.role not in ["WORKER", "READER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only delete WORKER and READER users."
            )

    # Store user info for logging before deletion
    user_info = {
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "dependency_id": user.dependency_id
    }

    # Update all references to this user to NULL before deletion
    # This prevents foreign key constraint violations
    
    # Update folders created/updated by this user
    db.query(Folder).filter(Folder.created_by == user_id).update(
        {"created_by": None}, synchronize_session=False
    )
    db.query(Folder).filter(Folder.updated_by == user_id).update(
        {"updated_by": None}, synchronize_session=False
    )
    
    # Update files uploaded by this user
    db.query(File).filter(File.uploaded_by == user_id).update(
        {"uploaded_by": None}, synchronize_session=False
    )
    
    # Update backups created by this user
    db.query(BackupRecord).filter(BackupRecord.created_by == user_id).update(
        {"created_by": None}, synchronize_session=False
    )
    
    # Update action logs for this user
    db.query(ActionLog).filter(ActionLog.user_id == user_id).update(
        {"user_id": None}, synchronize_session=False
    )
    
    # Delete refresh tokens for this user
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete(
        synchronize_session=False
    )
    
    # Commit the updates before deleting the user
    db.flush()

    # Hard delete - remove from database
    db.delete(user)
    db.commit()

    return {"message": "User permanently deleted successfully"}
