from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any, Optional
from collections import defaultdict

from ..models.folder import Folder
from ..models.file import File
from ..models.user import User

class FolderService:
    """Service for managing folder operations"""

    @staticmethod
    def build_folder_tree(db: Session, dependency_id: str) -> List[Dict[str, Any]]:
        """
        Build folder tree structure for a dependency

        Args:
            db: Database session
            dependency_id: Dependency ID to build tree for

        Returns:
            List of root folders with children
        """
        # Get all folders for the dependency in a single query
        folders = db.query(Folder).filter(Folder.dependency_id == dependency_id).all()

        # Create lookup dictionary
        folder_dict = {folder.id: {
            "id": folder.id,
            "name": folder.name,
            "path": folder.path,
            "parent_id": folder.parent_id,
            "dependency_id": folder.dependency_id,
            "created_by": folder.created_by,
            "created_at": folder.created_at.isoformat() if folder.created_at else None,
            "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
            "children": []
        } for folder in folders}

        # Build tree structure
        root_folders = []
        for folder in folders:
            if folder.parent_id:
                # Has parent, add to parent's children
                if folder.parent_id in folder_dict:
                    folder_dict[folder.parent_id]["children"].append(folder_dict[folder.id])
            else:
                # Root folder
                root_folders.append(folder_dict[folder.id])

        return root_folders

    @staticmethod
    def compute_folder_path(db: Session, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Compute the full path for a folder

        Args:
            db: Database session
            folder_name: Name of the folder
            parent_id: Parent folder ID (None for root)

        Returns:
            Full path string
        """
        if not parent_id:
            return folder_name

        parent = db.query(Folder).filter(Folder.id == parent_id).first()
        if not parent:
            raise ValueError(f"Parent folder {parent_id} not found")

        return f"{parent.path}/{folder_name}"

    @staticmethod
    def update_child_paths(db: Session, parent_id: str, new_parent_path: str):
        """
        Recursively update paths for all children of a folder

        Args:
            db: Database session
            parent_id: Parent folder ID
            new_parent_path: New path of the parent
        """
        def update_recursive(current_parent_id: str, current_parent_path: str):
            """Recursively update child folder paths"""
            children = db.query(Folder).filter(Folder.parent_id == current_parent_id).all()

            for child in children:
                # Update child's path
                child.path = f"{current_parent_path}/{child.name}"

                # Recursively update grandchildren
                update_recursive(child.id, child.path)

        # Start with direct children of the moved/renamed folder
        update_recursive(parent_id, new_parent_path)

        db.commit()

    @staticmethod
    def validate_folder_move(db: Session, folder_id: str, new_parent_id: Optional[str], current_user: User) -> None:
        """
        Validate that a folder can be moved to a new parent

        Args:
            db: Database session
            folder_id: Folder to move
            new_parent_id: New parent ID (None for root)
            current_user: Current user

        Raises:
            ValueError: If move is not allowed
        """
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise ValueError("Folder not found")

        # Check if moving to same parent
        if folder.parent_id == new_parent_id:
            return

        # Check if new parent exists and is in same dependency
        if new_parent_id:
            new_parent = db.query(Folder).filter(Folder.id == new_parent_id).first()
            if not new_parent:
                raise ValueError("New parent folder not found")
            if new_parent.dependency_id != folder.dependency_id:
                raise ValueError("Cannot move folder across different dependencies")
        else:
            # Moving to root - check if user has permission for this dependency
            if current_user.role != "SUPER_ADMIN" and current_user.dependency_id != folder.dependency_id:
                raise ValueError("Cannot move folder to root of different dependency")

        # Check for circular reference
        if new_parent_id:
            current_id = new_parent_id
            while current_id:
                if current_id == folder_id:
                    raise ValueError("Cannot move folder into its own subtree")
                parent = db.query(Folder).filter(Folder.id == current_id).first()
                current_id = parent.parent_id if parent else None

    @staticmethod
    def get_folder_stats(db: Session, folder_id: str) -> Dict[str, int]:
        """
        Get statistics for a folder (subfolders and files count)

        Args:
            db: Database session
            folder_id: Folder ID

        Returns:
            Dictionary with counts
        """
        # Count subfolders (recursive)
        subfolder_count = db.query(Folder).filter(
            Folder.path.like(f"%/{folder_id}/%") |
            Folder.path.like(f"%/{folder_id}")
        ).count()

        # Count files in this folder and subfolders
        folder_obj = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder_obj:
            return {"subfolders": 0, "files": 0}

        file_count = db.query(File).filter(
            File.folder_id == folder_id
        ).count()

        return {
            "subfolders": subfolder_count,
            "files": file_count
        }

# Global folder service instance
folder_service = FolderService()
