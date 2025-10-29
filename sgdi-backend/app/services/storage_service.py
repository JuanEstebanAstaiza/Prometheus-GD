import os
import hashlib
import shutil
import uuid
import unicodedata
import re
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, BinaryIO
from datetime import datetime
import tempfile

from ..core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    """Service for managing file storage operations"""

    def __init__(self):
        self.storage_path = Path(settings.storage_path)
        self.backup_path = Path(settings.backup_path)
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure storage directories exist"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.backup_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.storage_path / "temp").mkdir(exist_ok=True)
        (self.storage_path / "trash").mkdir(exist_ok=True)
        (self.storage_path / "dependencies").mkdir(exist_ok=True)

    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def save_file(self, file_content: bytes, filename: str, folder_path: str = "") -> Tuple[str, str]:
        """
        Save a file to storage and return the relative path and checksum

        Args:
            file_content: File content as bytes
            filename: Original filename
            folder_path: Relative folder path within storage

        Returns:
            Tuple of (relative_storage_path, checksum)
        """
        # Create folder structure
        folder_dir = self.storage_path / folder_path
        folder_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        file_path = folder_dir / unique_filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Calculate relative path and checksum
        relative_path = str(file_path.relative_to(self.storage_path))
        checksum = self.calculate_checksum(file_path)

        logger.info(f"File saved: {relative_path} (checksum: {checksum[:8]}...)")
        return relative_path, checksum

    def get_file_path(self, relative_path: str) -> Path:
        """Get absolute path for a relative storage path"""
        return self.storage_path / relative_path

    def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists in storage"""
        file_path = self.get_file_path(relative_path)
        return file_path.exists() and file_path.is_file()

    def read_file(self, relative_path: str) -> Optional[bytes]:
        """Read file content from storage"""
        file_path = self.get_file_path(relative_path)
        if not self.file_exists(relative_path):
            return None

        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {relative_path}: {e}")
            return None

    def delete_file(self, relative_path: str) -> bool:
        """Delete a file from storage"""
        file_path = self.get_file_path(relative_path)
        if not file_path.exists():
            return True

        try:
            file_path.unlink()
            logger.info(f"File deleted: {relative_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {relative_path}: {e}")
            return False

    def move_file(self, from_path: str, to_path: str) -> bool:
        """Move a file within storage"""
        from_file = self.get_file_path(from_path)
        to_file = self.get_file_path(to_path)

        if not from_file.exists():
            return False

        try:
            # Ensure destination directory exists
            to_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(from_file), str(to_file))
            logger.info(f"File moved: {from_path} -> {to_path}")
            return True
        except Exception as e:
            logger.error(f"Error moving file {from_path} to {to_path}: {e}")
            return False

    def copy_file(self, from_path: str, to_path: str) -> bool:
        """Copy a file within storage"""
        from_file = self.get_file_path(from_path)
        to_file = self.get_file_path(to_path)

        if not from_file.exists():
            return False

        try:
            # Ensure destination directory exists
            to_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(from_file), str(to_file))
            logger.info(f"File copied: {from_path} -> {to_path}")
            return True
        except Exception as e:
            logger.error(f"Error copying file {from_path} to {to_path}: {e}")
            return False

    def sanitize_filename(self, filename: str, max_length: int = 60) -> str:
        """
        Sanitize filename for use as base name

        Args:
            filename: Original filename
            max_length: Maximum length for sanitized name

        Returns:
            Sanitized filename safe for filesystem
        """
        # Remove extension
        name = Path(filename).stem

        # Normalize unicode
        name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')

        # Replace non-alphanumeric with underscore, keep dashes
        name = re.sub(r'[^a-zA-Z0-9\-_]', '_', name)

        # Replace multiple underscores with single
        name = re.sub(r'_+', '_', name)

        # Remove leading/trailing underscores
        name = name.strip('_')

        # Truncate if too long
        if len(name) > max_length:
            name = name[:max_length].rstrip('_')

        # Ensure not empty
        if not name:
            name = f"file_{uuid.uuid4().hex[:8]}"

        return name

    def save_temp_file(self, file_content: bytes, filename: str) -> Tuple[str, Path]:
        """
        Save file to temp directory with unique name

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Tuple of (temp_id, temp_file_path)
        """
        temp_id = str(uuid.uuid4())
        suffix = Path(filename).suffix if '.' in filename else ''
        temp_filename = f"{temp_id}{suffix}"
        temp_path = self.storage_path / "temp" / temp_filename

        # Ensure temp directory exists
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(temp_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved to temp: {temp_path}")
        return temp_id, temp_path

    def get_dependency_path(self, dependency_code: str) -> Path:
        """
        Get the base path for a dependency

        Args:
            dependency_code: Dependency code

        Returns:
            Path to dependency storage
        """
        return self.storage_path / "dependencies" / dependency_code

    def get_file_path(self, dependency_code: str, folder_path: str, filename: str) -> Path:
        """
        Get the full path for a file

        Args:
            dependency_code: Dependency code
            folder_path: Relative folder path within dependency
            filename: Stored filename

        Returns:
            Full path to file
        """
        dep_path = self.get_dependency_path(dependency_code)
        folder_rel_path = Path(folder_path.strip('/'))
        return dep_path / folder_rel_path / "files" / filename

    def get_version_path(self, dependency_code: str, folder_path: str, version_filename: str) -> Path:
        """
        Get the path for a file version

        Args:
            dependency_code: Dependency code
            folder_path: Relative folder path within dependency
            version_filename: Version filename

        Returns:
            Full path to version file
        """
        dep_path = self.get_dependency_path(dependency_code)
        folder_rel_path = Path(folder_path.strip('/'))
        return dep_path / folder_rel_path / "versions" / version_filename

    def move_temp_to_final(self, temp_path: Path, final_path: Path) -> bool:
        """
        Atomically move temp file to final location

        Args:
            temp_path: Temp file path
            final_path: Final destination path

        Returns:
            True if successful
        """
        try:
            # Ensure destination directory exists
            final_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic move
            os.replace(str(temp_path), str(final_path))
            logger.info(f"File moved from temp to final: {final_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to move temp file to final: {e}")
            return False

    def create_file_version(self, current_path: Path, version_path: Path) -> bool:
        """
        Create a version copy of the current file

        Args:
            current_path: Current file path
            version_path: Version file path

        Returns:
            True if successful
        """
        try:
            # Ensure version directory exists
            version_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy current file to version
            shutil.copy2(str(current_path), str(version_path))
            logger.info(f"File version created: {version_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create file version: {e}")
            return False

    def generate_version_filename(self, file_id: str, version: int, original_filename: str) -> str:
        """
        Generate version filename

        Args:
            file_id: File ID
            version: Version number
            original_filename: Original filename

        Returns:
            Version filename
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        suffix = Path(original_filename).suffix
        return f"{file_id}_v{version}_{timestamp}{suffix}"

    def move_to_trash(self, file_path: Path, reason: str = "deleted") -> bool:
        """
        Move file to trash directory

        Args:
            file_path: File to move
            reason: Reason for moving to trash

        Returns:
            True if successful
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = file_path.name
            trash_filename = f"{timestamp}_{reason}_{filename}"
            trash_path = self.storage_path / "trash" / trash_filename

            # Ensure trash directory exists
            trash_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file to trash
            shutil.move(str(file_path), str(trash_path))
            logger.info(f"File moved to trash: {trash_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to move file to trash: {e}")
            return False

    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate file size against limits

        Args:
            file_size: File size in bytes

        Returns:
            True if valid
        """
        return file_size <= settings.max_upload_size_bytes

    def validate_mime_type(self, mime_type: str) -> bool:
        """
        Validate MIME type against allowed types

        Args:
            mime_type: MIME type to validate

        Returns:
            True if allowed
        """
        return mime_type in settings.allowed_mime_types_list

    def get_storage_info(self) -> dict:
        """Get storage information"""
        try:
            total_size = sum(f.stat().st_size for f in self.storage_path.rglob('*') if f.is_file())
            file_count = sum(1 for f in self.storage_path.rglob('*') if f.is_file())

            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "storage_path": str(self.storage_path),
                "writable": os.access(self.storage_path, os.W_OK)
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                "error": str(e),
                "storage_path": str(self.storage_path),
                "writable": False
            }

# Global storage service instance
storage_service = StorageService()
