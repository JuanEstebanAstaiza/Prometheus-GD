from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ..core.database import get_db
from ..core.auth import get_current_active_user, require_super_admin, require_admin_dep_or_super
from ..models.dependency import Dependency
from ..models.folder import Folder
from ..schemas.dependencies import (
    DependencyCreate, DependencyUpdate, DependencyResponse, DependencyList
)
from ..schemas.common import ErrorResponse, NotFoundResponse, ConflictResponse
from ..services.audit_service import audit_service

router = APIRouter()

# Definir ambas rutas (con y sin barra final) para evitar problemas con redirect_slashes=False
@router.get("", response_model=DependencyList, responses={
    200: {"model": DependencyList}
})
@router.get("/", response_model=DependencyList, responses={
    200: {"model": DependencyList}
})
async def read_dependencies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Dependency = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve dependencies based on user permissions

    - Super admin: returns all dependencies
    - Admin: returns only their dependency
    - Worker/Reader: returns their dependency info
    """
    query = db.query(Dependency)

    # Apply permission-based filtering
    if current_user.role == "SUPER_ADMIN":
        # Super admin sees all dependencies
        pass
    elif current_user.role == "ADMIN_DEP":
        # Admin sees only their dependency
        if current_user.dependency_id:
            query = query.filter(Dependency.id == current_user.dependency_id)
        else:
            # Admin without dependency - no access
            return {"items": [], "total": 0}
    else:
        # Worker/Reader see only their dependency
        if current_user.dependency_id:
            query = query.filter(Dependency.id == current_user.dependency_id)
        else:
            # User without dependency - no access
            return {"items": [], "total": 0}

    # Get total count
    total = query.count()

    # Get paginated results
    dependencies = query.offset(skip).limit(limit).all()

    # Add counters to each dependency
    from ..models.user import User
    from ..models.file import File
    
    items_with_counts = []
    for dep in dependencies:
        # Count users in this dependency
        user_count = db.query(User).filter(User.dependency_id == dep.id).count()
        
        # Count folders in this dependency
        folder_count = db.query(Folder).filter(Folder.dependency_id == dep.id).count()
        
        # Count files in this dependency
        file_count = db.query(File).filter(File.dependency_id == dep.id).count()
        
        # Convert to dict and add counts
        dep_dict = {
            "id": dep.id,
            "name": dep.name,
            "code": dep.code,
            "created_at": dep.created_at.isoformat() if dep.created_at else None,
            "updated_at": dep.updated_at.isoformat() if dep.updated_at else None,
            "user_count": user_count,
            "folder_count": folder_count,
            "file_count": file_count
        }
        items_with_counts.append(dep_dict)

    return {"items": items_with_counts, "total": total}

@router.post("", response_model=DependencyResponse, status_code=status.HTTP_201_CREATED, responses={
    201: {"model": DependencyResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    409: {"model": ConflictResponse}
})
@router.post("/", response_model=DependencyResponse, status_code=status.HTTP_201_CREATED, responses={
    201: {"model": DependencyResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    409: {"model": ConflictResponse}
})
async def create_dependency(
    dependency: DependencyCreate,
    current_user: Dependency = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Create new dependency (Super admin only)

    Creates dependency record and root folder automatically.
    """
    # Check if code already exists
    existing = db.query(Dependency).filter(
        or_(Dependency.code == dependency.code.upper(),
            Dependency.name == dependency.name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dependency with code '{dependency.code}' or name '{dependency.name}' already exists"
        )

    # Create dependency
    db_dependency = Dependency(
        id=str(uuid.uuid4()),
        name=dependency.name,
        code=dependency.code.upper()
    )

    db.add(db_dependency)
    db.flush()  # Get the ID

    # Create root folder for dependency
    root_folder = Folder(
        id=str(uuid.uuid4()),
        name=dependency.name,
        path=dependency.name,
        dependency_id=db_dependency.id,
        created_by=current_user.id,
        updated_by=current_user.id
    )

    db.add(root_folder)
    db.commit()
    db.refresh(db_dependency)

    # Log audit events
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="CREATE_DEPENDENCY",
        target_type="DEPENDENCY",
        target_id=db_dependency.id,
        details={
            "name": db_dependency.name,
            "code": db_dependency.code
        }
    )

    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="CREATE_FOLDER",
        target_type="FOLDER",
        target_id=root_folder.id,
        details={
            "name": root_folder.name,
            "path": root_folder.path,
            "dependency_id": root_folder.dependency_id,
            "is_root": True
        }
    )

    return db_dependency

@router.get("/{dependency_id}", response_model=DependencyResponse, responses={
    200: {"model": DependencyResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def read_dependency(
    dependency_id: str,
    current_user: Dependency = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dependency by ID with permission checks
    """
    dependency = db.query(Dependency).filter(Dependency.id == dependency_id).first()
    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found"
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.role == "ADMIN_DEP" and current_user.dependency_id != dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your own dependency."
            )
        elif current_user.dependency_id != dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your assigned dependency."
            )

    return dependency

@router.put("/{dependency_id}", response_model=DependencyResponse, responses={
    200: {"model": DependencyResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse},
    409: {"model": ConflictResponse}
})
async def update_dependency(
    dependency_id: str,
    dependency_update: DependencyUpdate,
    current_user: Dependency = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Update dependency (Super admin only)
    """
    dependency = db.query(Dependency).filter(Dependency.id == dependency_id).first()
    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found"
        )

    # Check for conflicts
    update_data = dependency_update.dict(exclude_unset=True)

    if "code" in update_data:
        existing = db.query(Dependency).filter(
            and_(Dependency.code == update_data["code"].upper(),
                 Dependency.id != dependency_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dependency with code '{update_data['code']}' already exists"
            )
        update_data["code"] = update_data["code"].upper()

    if "name" in update_data:
        existing = db.query(Dependency).filter(
            and_(Dependency.name == update_data["name"],
                 Dependency.id != dependency_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dependency with name '{update_data['name']}' already exists"
            )

    # Update dependency
    for field, value in update_data.items():
        setattr(dependency, field, value)

    db.commit()
    db.refresh(dependency)

    # Log audit event
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="UPDATE_DEPENDENCY",
        target_type="DEPENDENCY",
        target_id=dependency.id,
        details=update_data
    )

    return dependency

@router.delete("/{dependency_id}", responses={
    204: {"description": "Dependency deleted successfully"},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse},
    409: {"model": ConflictResponse}
})
async def delete_dependency(
    dependency_id: str,
    force: bool = Query(False, description="Force deletion even if dependency has content"),
    current_user: Dependency = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Delete dependency (Super admin only)

    Checks for existing folders/files and requires force=true if any exist.
    """
    dependency = db.query(Dependency).filter(Dependency.id == dependency_id).first()
    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found"
        )

    # Check for existing content
    folder_count = db.query(Folder).filter(Folder.dependency_id == dependency_id).count()

    if folder_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dependency has {folder_count} folders. Use force=true to delete anyway."
        )

    # Delete dependency (cascade will handle folders/files)
    db.delete(dependency)
    db.commit()

    # Log audit event
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="DELETE_DEPENDENCY",
        target_type="DEPENDENCY",
        target_id=dependency_id,
        details={
            "name": dependency.name,
            "code": dependency.code,
            "force": force,
            "folders_deleted": folder_count
        }
    )

    return {"message": "Dependency deleted successfully"}
