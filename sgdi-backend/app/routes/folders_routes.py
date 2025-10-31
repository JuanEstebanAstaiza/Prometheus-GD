from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid

from ..core.database import get_db
from ..core.auth import get_current_active_user, require_admin_dep_or_super
from ..models.folder import Folder
from ..models.dependency import Dependency
from ..models.file import File
from ..schemas.folders import (
    FolderCreate, FolderUpdate, FolderResponse, FolderTreeNode,
    FolderDeleteRequest, FolderDeleteResponse
)
from ..schemas.common import ErrorResponse, NotFoundResponse, ConflictResponse
from ..services.folder_service import folder_service
from ..services.audit_service import audit_service

router = APIRouter()

@router.get("/dependencies/{dependency_id}/tree", response_model=List[FolderTreeNode], responses={
    200: {"model": List[FolderTreeNode]},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def get_dependency_folder_tree(
    dependency_id: str,
    current_user: Folder = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get folder tree for a dependency

    Returns hierarchical folder structure with children.
    """
    # Check if dependency exists
    dependency = db.query(Dependency).filter(Dependency.id == dependency_id).first()
    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found"
        )

    # Check permissions: Users can view their own dependency OR GLOBAL
    if current_user.role != "SUPER_ADMIN":
        # Check if trying to access GLOBAL
        if dependency.code == "GLOBAL":
            # Everyone can view GLOBAL folders
            pass
        elif current_user.dependency_id != dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view folders in your assigned dependency or GLOBAL."
            )

    # Build and return folder tree
    tree = folder_service.build_folder_tree(db, dependency_id)
    return tree

@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED, responses={
    201: {"model": FolderResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse},
    409: {"model": ConflictResponse}
})
@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED, responses={
    201: {"model": FolderResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse},
    409: {"model": ConflictResponse}
})
async def create_folder(
    folder: FolderCreate,
    current_user: Folder = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Create new folder with permission checks

    Validates parent belongs to same dependency and computes path.
    """
    # Check if dependency exists
    dependency = db.query(Dependency).filter(Dependency.id == folder.dependency_id).first()
    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found"
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id != folder.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only create folders in your assigned dependency."
            )

    # Validate parent folder if specified
    if folder.parent_id:
        parent = db.query(Folder).filter(Folder.id == folder.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent folder not found"
            )
        if parent.dependency_id != folder.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent folder must be in the same dependency"
            )

    # Check for name conflicts in the same parent
    existing = db.query(Folder).filter(
        and_(
            Folder.name == folder.name,
            Folder.parent_id == folder.parent_id,
            Folder.dependency_id == folder.dependency_id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Folder with name '{folder.name}' already exists in this location"
        )

    # Compute path
    try:
        path = folder_service.compute_folder_path(db, folder.name, folder.parent_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Create folder
    db_folder = Folder(
        id=str(uuid.uuid4()),
        name=folder.name,
        path=path,
        parent_id=folder.parent_id,
        dependency_id=folder.dependency_id,
        created_by=current_user.id,
        updated_by=current_user.id
    )

    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)

    # Log audit event
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="CREATE_FOLDER",
        target_type="FOLDER",
        target_id=db_folder.id,
        details={
            "name": db_folder.name,
            "path": db_folder.path,
            "parent_id": db_folder.parent_id,
            "dependency_id": db_folder.dependency_id
        }
    )

    return db_folder

@router.get("/{folder_id}", response_model=FolderResponse, responses={
    200: {"model": FolderResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse}
})
async def read_folder(
    folder_id: str,
    current_user: Folder = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get folder by ID with permission checks
    """
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id != folder.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access folders in your assigned dependency."
            )

    return folder

@router.put("/{folder_id}", response_model=FolderResponse, responses={
    200: {"model": FolderResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse},
    409: {"model": ConflictResponse}
})
async def update_folder(
    folder_id: str,
    folder_update: FolderUpdate,
    current_user: Folder = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Update folder (rename or move) with path propagation

    Supports renaming and moving folders, updating paths recursively.
    """
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id != folder.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only modify folders in your assigned dependency."
            )

    update_data = folder_update.dict(exclude_unset=True)

    # Store old values for audit
    old_values = {
        "name": folder.name,
        "path": folder.path,
        "parent_id": folder.parent_id
    }

    # Validate move operation
    if "parent_id" in update_data:
        try:
            folder_service.validate_folder_move(db, folder_id, update_data["parent_id"], current_user)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    # Handle rename or move
    name_changed = "name" in update_data and update_data["name"] != folder.name
    parent_changed = "parent_id" in update_data and update_data["parent_id"] != folder.parent_id

    if name_changed or parent_changed:
        new_name = update_data.get("name", folder.name)
        new_parent_id = update_data.get("parent_id", folder.parent_id)

        # Check for name conflicts
        existing = db.query(Folder).filter(
            and_(
                Folder.name == new_name,
                Folder.parent_id == new_parent_id,
                Folder.dependency_id == folder.dependency_id,
                Folder.id != folder_id
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Folder with name '{new_name}' already exists in this location"
            )

        # Compute new path
        try:
            new_path = folder_service.compute_folder_path(db, new_name, new_parent_id)
            update_data["path"] = new_path
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    # Update folder
    for field, value in update_data.items():
        setattr(folder, field, value)

    # If path changed, update all children paths
    if "path" in update_data and update_data["path"] != old_values["path"]:
        folder_service.update_child_paths(db, folder_id, folder.path)

    db.commit()
    db.refresh(folder)

    # Log audit event
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="UPDATE_FOLDER",
        target_type="FOLDER",
        target_id=folder.id,
        details={
            "old_values": old_values,
            "new_values": update_data,
            "path_updated": "path" in update_data,
            "children_paths_updated": "path" in update_data
        }
    )

    return folder

@router.delete("/{folder_id}", responses={
    200: {"model": FolderDeleteResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": NotFoundResponse},
    409: {"model": ConflictResponse}
})
async def delete_folder(
    folder_id: str,
    force: bool = Query(False, description="Force deletion even if folder contains items"),
    current_user: Folder = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Delete folder with content validation

    If folder has contents, requires force=true parameter.
    """
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Check permissions
    if current_user.role != "SUPER_ADMIN":
        if current_user.dependency_id != folder.dependency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only delete folders in your assigned dependency."
            )

    # Get folder statistics
    stats = folder_service.get_folder_stats(db, folder_id)
    has_contents = stats["subfolders"] > 0 or stats["files"] > 0

    if has_contents and not force:
        return FolderDeleteResponse(
            deleted=False,
            items_deleted={"subfolders": stats["subfolders"], "files": stats["files"]},
            message=f"Folder contains {stats['subfolders']} subfolders and {stats['files']} files. Use force=true to delete."
        )

    # Delete folder (cascade will handle subfolders and files)
    db.delete(folder)
    db.commit()

    # Log audit event
    audit_service.log_action(
        db=db,
        user=current_user,
        action_type="DELETE_FOLDER",
        target_type="FOLDER",
        target_id=folder_id,
        details={
            "name": folder.name,
            "path": folder.path,
            "force": force,
            "items_deleted": stats if has_contents else None
        }
    )

    return FolderDeleteResponse(
        deleted=True,
        items_deleted=stats if has_contents else None,
        message="Folder deleted successfully"
    )
