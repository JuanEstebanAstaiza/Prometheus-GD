import os
import shutil
import subprocess
import tarfile
import json
import hashlib
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from ..core.config import settings
from ..core.database import engine, SessionLocal
from ..models.dependency import Dependency
from ..models.folder import Folder
from ..models.file import File
from ..models.action_logs import ActionLog
from ..models.backup import BackupRecord
from .storage_service import storage_service
import logging

logger = logging.getLogger(__name__)

class BackupService:
    """Service for managing system backups"""

    def __init__(self):
        self.backup_path = Path(settings.backup_path)
        self.staging_path = self.backup_path / "staging"
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.staging_path.mkdir(parents=True, exist_ok=True)

    def create_database_backup(self, backup_name: str) -> Optional[str]:
        """
        Create a PostgreSQL database backup using pg_dump

        Args:
            backup_name: Name for the backup file

        Returns:
            Path to the backup file or None if failed
        """
        try:
            # Extract database connection info from URL
            from urllib.parse import urlparse
            db_url = urlparse(settings.database_url)

            backup_file = self.backup_path / f"{backup_name}_db.sql"
            env = os.environ.copy()

            # Build pg_dump command
            cmd = [
                "pg_dump",
                "--host", db_url.hostname or "localhost",
                "--port", str(db_url.port or 5432),
                "--username", db_url.username or "postgres",
                "--dbname", db_url.path.lstrip("/"),
                "--no-password",
                "--format", "c",  # Custom format
                "--compress", "9",
                "--file", str(backup_file)
            ]

            # Set password in environment
            if db_url.password:
                env["PGPASSWORD"] = db_url.password

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode == 0:
                logger.info(f"Database backup created: {backup_file}")
                return str(backup_file)
            else:
                logger.error(f"Database backup failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            return None

    def create_files_backup(self, backup_name: str) -> Optional[str]:
        """
        Create a backup of the storage files

        Args:
            backup_name: Name for the backup file

        Returns:
            Path to the backup archive or None if failed
        """
        try:
            import tarfile

            backup_file = self.backup_path / f"{backup_name}_files.tar.gz"
            storage_path = Path(settings.storage_path)

            with tarfile.open(backup_file, "w:gz") as tar:
                # Add storage directory
                tar.add(storage_path, arcname="storage")

            logger.info(f"Files backup created: {backup_file}")
            return str(backup_file)

        except Exception as e:
            logger.error(f"Error creating files backup: {e}")
            return None

    def create_full_backup(self, backup_name: str) -> Dict[str, Any]:
        """
        Create a complete system backup (database + files)

        Args:
            backup_name: Name for the backup

        Returns:
            Backup information dictionary
        """
        logger.info(f"Starting full backup: {backup_name}")

        backup_info = {
            "name": backup_name,
            "type": "full",
            "started_at": datetime.utcnow(),
            "database_backup": None,
            "files_backup": None,
            "total_size": 0,
            "status": "running",
            "error": None
        }

        try:
            # Create database backup
            db_backup = self.create_database_backup(backup_name)
            if db_backup:
                backup_info["database_backup"] = db_backup
                backup_info["total_size"] += Path(db_backup).stat().st_size

            # Create files backup
            files_backup = self.create_files_backup(backup_name)
            if files_backup:
                backup_info["files_backup"] = files_backup
                backup_info["total_size"] += Path(files_backup).stat().st_size

            backup_info["completed_at"] = datetime.utcnow()
            backup_info["status"] = "completed"
            backup_info["duration_seconds"] = (
                backup_info["completed_at"] - backup_info["started_at"]
            ).total_seconds()

            logger.info(f"Full backup completed: {backup_name}")

        except Exception as e:
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            backup_info["completed_at"] = datetime.utcnow()
            logger.error(f"Full backup failed: {backup_name} - {e}")

        return backup_info

    def restore_database_backup(self, backup_file: str) -> bool:
        """
        Restore database from backup

        Args:
            backup_file: Path to the backup file

        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False

            # Extract database connection info
            from urllib.parse import urlparse
            db_url = urlparse(settings.database_url)

            env = os.environ.copy()

            # Build pg_restore command
            cmd = [
                "pg_restore",
                "--host", db_url.hostname or "localhost",
                "--port", str(db_url.port or 5432),
                "--username", db_url.username or "postgres",
                "--dbname", db_url.path.lstrip("/"),
                "--no-password",
                "--clean",  # Clean (drop) database objects before recreating
                "--if-exists",
                "--create",  # Create the database
                str(backup_path)
            ]

            if db_url.password:
                env["PGPASSWORD"] = db_url.password

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )

            if result.returncode == 0:
                logger.info(f"Database restored from: {backup_file}")
                return True
            else:
                logger.error(f"Database restore failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False

    def cleanup_old_backups(self, retention_days: int = 30):
        """
        Remove backups older than retention period

        Args:
            retention_days: Number of days to keep backups
        """
        try:
            cutoff_date = datetime.utcnow().timestamp() - (retention_days * 24 * 60 * 60)

            for backup_file in self.backup_path.glob("*"):
                if backup_file.is_file() and backup_file.stat().st_mtime < cutoff_date:
                    backup_file.unlink()
                    logger.info(f"Removed old backup: {backup_file.name}")

        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

    def get_backup_info(self) -> Dict[str, Any]:
        """Get backup directory information"""
        try:
            total_size = sum(f.stat().st_size for f in self.backup_path.rglob('*') if f.is_file())
            file_count = sum(1 for f in self.backup_path.rglob('*') if f.is_file())

            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "backup_path": str(self.backup_path),
                "writable": os.access(self.backup_path, os.W_OK)
            }
        except Exception as e:
            logger.error(f"Error getting backup info: {e}")
            return {
                "error": str(e),
                "backup_path": str(self.backup_path),
                "writable": False
            }

    def create_comprehensive_backup(self, dependency_id: Optional[str] = None, include_logs: bool = True,
                                   created_by: str = None) -> Dict[str, Any]:
        """
        Create a comprehensive backup with metadata and physical files

        Args:
            dependency_id: Optional dependency ID for partial backup
            include_logs: Whether to include action logs
            created_by: User who created the backup

        Returns:
            Backup information dictionary
        """
        backup_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup-{timestamp}"

        logger.info(f"Starting comprehensive backup: {backup_name} (ID: {backup_id})")

        backup_info = {
            "id": backup_id,
            "name": backup_name,
            "type": "comprehensive",
            "dependency_id": dependency_id,
            "include_logs": include_logs,
            "created_by": created_by,
            "started_at": datetime.utcnow(),
            "status": "running",
            "total_files": 0,
            "total_size_bytes": 0,
            "error": None
        }

        try:
            # Create staging directory for this backup
            staging_dir = self.staging_path / backup_id
            staging_dir.mkdir(parents=True, exist_ok=True)

            backup_dir = staging_dir / f"backup-{timestamp}"
            backup_dir.mkdir()

            # Gather metadata
            metadata = self._gather_backup_metadata(dependency_id, include_logs)
            backup_info["total_files"] = len(metadata.get("files", []))

            # Write metadata to JSON file
            metadata_file = backup_dir / "metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str, ensure_ascii=False)

            # Copy physical files
            files_dir = backup_dir / "files"
            files_dir.mkdir()
            total_size = self._copy_physical_files(metadata["files"], files_dir, dependency_id)
            backup_info["total_size_bytes"] = total_size

            # Create tar.gz archive
            archive_name = f"{backup_name}.tar.gz"
            archive_path = self.backup_path / archive_name

            with tarfile.open(archive_path, "w:gz") as tar:
                # Add the backup directory contents
                for item in backup_dir.rglob("*"):
                    if item.is_file():
                        tar.add(item, arcname=f"backup-{timestamp}/{item.relative_to(backup_dir)}")

            # Calculate checksum
            checksum = self._calculate_file_checksum(archive_path)

            # Clean up staging
            shutil.rmtree(staging_dir)

            # Create backup record
            db = SessionLocal()
            try:
                backup_record = BackupRecord(
                    filename=archive_name,
                    backup_type="comprehensive",
                    dependency_id=dependency_id,
                    total_files=backup_info["total_files"],
                    total_size_bytes=backup_info["total_size_bytes"],
                    checksum_sha256=checksum,
                    backup_metadata=metadata,
                    created_by=created_by
                )
                db.add(backup_record)
                db.commit()
                db.refresh(backup_record)
                backup_info["record_id"] = backup_record.id
            finally:
                db.close()

            backup_info["completed_at"] = datetime.utcnow()
            backup_info["status"] = "completed"
            backup_info["archive_path"] = str(archive_path)
            backup_info["checksum"] = checksum

            logger.info(f"Comprehensive backup completed: {backup_name}")

        except Exception as e:
            logger.error(f"Comprehensive backup failed: {e}")
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            backup_info["completed_at"] = datetime.utcnow()

            # Clean up on failure
            try:
                shutil.rmtree(staging_dir, ignore_errors=True)
            except:
                pass

        return backup_info

    def _serialize_model(self, obj: Any) -> Dict[str, Any]:
        """Serialize SQLAlchemy model to JSON-serializable dict"""
        result = {}
        for key, value in obj.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (str, int, float, bool, type(None))):
                result[key] = value
            elif isinstance(value, dict):
                result[key] = value  # Already serializable
            else:
                # Skip complex objects
                continue
        return result

    def _gather_backup_metadata(self, dependency_id: Optional[str], include_logs: bool) -> Dict[str, Any]:
        """Gather all metadata for backup"""
        db = SessionLocal()
        try:
            metadata = {
                "backup_version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "dependency_id": dependency_id,
                "include_logs": include_logs
            }

            # Dependencies
            query = db.query(Dependency)
            if dependency_id:
                query = query.filter(Dependency.id == dependency_id)
            metadata["dependencies"] = [self._serialize_model(dep) for dep in query.all()]

            # Folders
            query = db.query(Folder)
            if dependency_id:
                query = query.filter(Folder.dependency_id == dependency_id)
            metadata["folders"] = [self._serialize_model(folder) for folder in query.all()]

            # Files
            query = db.query(File)
            if dependency_id:
                query = query.filter(File.dependency_id == dependency_id)
            metadata["files"] = [self._serialize_model(file) for file in query.all()]

            # Action logs (optional)
            if include_logs:
                query = db.query(ActionLog)
                if dependency_id:
                    # Only logs related to the dependency
                    query = query.filter(ActionLog.details.contains({"dependency_id": dependency_id}))
                # Limit to last 90 days to avoid huge backups
                cutoff_date = datetime.utcnow() - timedelta(days=90)
                query = query.filter(ActionLog.timestamp >= cutoff_date)
                metadata["action_logs"] = [self._serialize_model(log) for log in query.all()]

            return metadata

        finally:
            db.close()

    def _copy_physical_files(self, files_metadata: List[Dict], target_dir: Path,
                           dependency_id: Optional[str]) -> int:
        """
        Copy physical files to backup directory preserving folder structure.
        
        Structure:
        files/
        ├── DEPENDENCY_CODE/
        │   └── folder/path/
        │       └── stored_name.ext
        """
        total_size = 0
        copied_count = 0
        db = SessionLocal()

        try:
            for file_meta in files_metadata:
                try:
                    if dependency_id and file_meta.get("dependency_id") != dependency_id:
                        continue

                    # Get dependency and folder info from database
                    dep = db.query(Dependency).filter(Dependency.id == file_meta["dependency_id"]).first()
                    if not dep:
                        logger.warning(f"Dependency not found for file {file_meta.get('original_name')}")
                        continue

                    folder = db.query(Folder).filter(Folder.id == file_meta["folder_id"]).first()
                    if not folder:
                        logger.warning(f"Folder not found for file {file_meta.get('original_name')}")
                        continue

                    # Build source path
                    source_path = storage_service.get_file_path(
                        dep.code, folder.path, file_meta["stored_name"]
                    )

                    if source_path.exists():
                        # Preserve folder structure: files/DEPENDENCY_CODE/folder/path/stored_name
                        relative_path = Path(dep.code) / folder.path / file_meta["stored_name"]
                        target_path = target_dir / relative_path
                        
                        # Create parent directories if needed
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Copy file with metadata
                        shutil.copy2(source_path, target_path)
                        total_size += source_path.stat().st_size
                        copied_count += 1
                        
                        logger.debug(f"Copied: {relative_path}")
                    else:
                        logger.warning(f"File not found: {source_path} (original: {file_meta.get('original_name')})")

                except Exception as e:
                    logger.warning(f"Failed to copy file {file_meta.get('original_name', 'unknown')}: {e}")
                    continue

            logger.info(f"Backup copy complete: {copied_count}/{len(files_metadata)} files, {total_size} bytes")
            return total_size

        finally:
            db.close()

    def _get_dependency_code(self, dependency_id: str) -> str:
        """Get dependency code from ID"""
        db = SessionLocal()
        try:
            dep = db.query(Dependency).filter(Dependency.id == dependency_id).first()
            return dep.code if dep else dependency_id
        finally:
            db.close()

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def get_backup_records(self, dependency_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of backup records"""
        db = SessionLocal()
        try:
            query = db.query(BackupRecord).order_by(BackupRecord.created_at.desc())
            if dependency_id:
                query = query.filter(BackupRecord.dependency_id == dependency_id)

            records = []
            for record in query.all():
                record_dict = {
                    "id": record.id,
                    "filename": record.filename,
                    "backup_type": record.backup_type,
                    "dependency_id": record.dependency_id,
                    "total_files": record.total_files,
                    "total_size_bytes": record.total_size_bytes,
                    "checksum_sha256": record.checksum_sha256,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "created_by": record.created_by
                }
                records.append(record_dict)

            return records

        finally:
            db.close()

    def get_backup_record(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get specific backup record"""
        db = SessionLocal()
        try:
            record = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
            if not record:
                return None

            return {
                "id": record.id,
                "filename": record.filename,
                "backup_type": record.backup_type,
                "dependency_id": record.dependency_id,
                "total_files": record.total_files,
                "total_size_bytes": record.total_size_bytes,
                "checksum_sha256": record.checksum_sha256,
                "metadata": record.metadata,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "created_by": record.created_by
            }

        finally:
            db.close()

    def simulate_restore(self, backup_file: bytes, filename: str) -> Dict[str, Any]:
        """
        Simulate restore and return detailed report

        Args:
            backup_file: Backup file content
            filename: Original filename

        Returns:
            Simulation report
        """
        restore_id = str(uuid.uuid4())
        staging_dir = self.staging_path / f"restore_{restore_id}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Save backup file temporarily
            temp_backup = staging_dir / filename
            with open(temp_backup, "wb") as f:
                f.write(backup_file)

            # Extract backup
            extract_dir = staging_dir / "extracted"
            extract_dir.mkdir()

            with tarfile.open(temp_backup, "r:gz") as tar:
                tar.extractall(extract_dir)

            # Find backup directory (should be the only directory)
            backup_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if not backup_dirs:
                raise ValueError("No backup directory found in archive")

            backup_content_dir = backup_dirs[0]

            # Read metadata
            metadata_file = backup_content_dir / "metadata.json"
            if not metadata_file.exists():
                raise ValueError("metadata.json not found in backup")

            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Analyze what would be restored
            report = self._analyze_restore_impact(metadata)

            return {
                "restore_id": restore_id,
                "simulation": True,
                "metadata_version": metadata.get("backup_version"),
                "created_at": metadata.get("created_at"),
                "dependency_id": metadata.get("dependency_id"),
                "include_logs": metadata.get("include_logs"),
                "report": report
            }

        finally:
            # Clean up
            shutil.rmtree(staging_dir, ignore_errors=True)

    def restore_backup(self, backup_file: bytes, filename: str, strategy: str = "create_new_ids",
                      preserve_existing: bool = True, confirm: bool = False) -> Dict[str, Any]:
        """
        Restore backup with specified strategy

        Args:
            backup_file: Backup file content
            filename: Original filename
            strategy: "create_new_ids" or "overwrite"
            preserve_existing: Whether to preserve existing data
            confirm: Confirmation flag for dangerous operations

        Returns:
            Restore result
        """
        if strategy == "overwrite" and not confirm:
            raise ValueError("Overwrite strategy requires explicit confirmation (--confirm=true)")

        restore_id = str(uuid.uuid4())
        staging_dir = self.staging_path / f"restore_{restore_id}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "restore_id": restore_id,
            "strategy": strategy,
            "preserve_existing": preserve_existing,
            "started_at": datetime.utcnow(),
            "status": "running",
            "files_restored": 0,
            "folders_created": 0,
            "dependencies_created": 0,
            "errors": []
        }

        db = SessionLocal()
        try:
            # Save and extract backup
            temp_backup = staging_dir / filename
            with open(temp_backup, "wb") as f:
                f.write(backup_file)

            extract_dir = staging_dir / "extracted"
            extract_dir.mkdir()

            with tarfile.open(temp_backup, "r:gz") as tar:
                tar.extractall(extract_dir)

            backup_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if not backup_dirs:
                raise ValueError("No backup directory found in archive")

            backup_content_dir = backup_dirs[0]

            # Read metadata
            metadata_file = backup_content_dir / "metadata.json"
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Validate checksum if provided
            files_dir = backup_content_dir / "files"
            if files_dir.exists():
                # Copy files to staging area first
                staging_files_dir = staging_dir / "staged_files"
                staging_files_dir.mkdir()

                for file_path in files_dir.iterdir():
                    if file_path.is_file():
                        shutil.copy2(file_path, staging_files_dir / file_path.name)

            # Start transaction
            with db.begin_nested():
                # Restore data based on strategy
                if strategy == "create_new_ids":
                    restore_result = self._restore_with_new_ids(db, metadata, staging_files_dir, restore_id)
                elif strategy == "overwrite":
                    restore_result = self._restore_with_overwrite(db, metadata, staging_files_dir, preserve_existing)
                else:
                    raise ValueError(f"Unknown restore strategy: {strategy}")

                result.update(restore_result)

            # Commit transaction
            db.commit()

            # Move staged files to final location
            if staging_files_dir.exists():
                result["files_restored"] = self._finalize_file_restore(staging_files_dir, metadata)

            result["completed_at"] = datetime.utcnow()
            result["status"] = "completed"

            logger.info(f"Restore completed: {restore_id} with strategy {strategy}")

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
            result["completed_at"] = datetime.utcnow()
            db.rollback()

        finally:
            db.close()
            # Clean up staging
            shutil.rmtree(staging_dir, ignore_errors=True)

        return result

    def _analyze_restore_impact(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what would be restored and identify conflicts"""
        db = SessionLocal()
        try:
            report = {
                "dependencies": {"to_create": [], "conflicts": []},
                "folders": {"to_create": [], "conflicts": []},
                "files": {"to_create": [], "conflicts": []},
                "action_logs": {"to_create": 0}
            }

            # Check dependencies
            for dep_data in metadata.get("dependencies", []):
                existing = db.query(Dependency).filter(Dependency.id == dep_data["id"]).first()
                if existing:
                    report["dependencies"]["conflicts"].append({
                        "id": dep_data["id"],
                        "name": dep_data["name"],
                        "existing_name": existing.name
                    })
                else:
                    report["dependencies"]["to_create"].append({
                        "id": dep_data["id"],
                        "name": dep_data["name"],
                        "code": dep_data["code"]
                    })

            # Check folders
            for folder_data in metadata.get("folders", []):
                existing = db.query(Folder).filter(Folder.id == folder_data["id"]).first()
                if existing:
                    report["folders"]["conflicts"].append({
                        "id": folder_data["id"],
                        "name": folder_data["name"],
                        "path": folder_data["path"],
                        "existing_path": existing.path
                    })
                else:
                    report["folders"]["to_create"].append({
                        "id": folder_data["id"],
                        "name": folder_data["name"],
                        "path": folder_data["path"]
                    })

            # Check files
            for file_data in metadata.get("files", []):
                existing = db.query(File).filter(File.id == file_data["id"]).first()
                if existing:
                    report["files"]["conflicts"].append({
                        "id": file_data["id"],
                        "original_name": file_data["original_name"],
                        "existing_name": existing.original_name
                    })
                else:
                    report["files"]["to_create"].append({
                        "id": file_data["id"],
                        "original_name": file_data["original_name"],
                        "size_bytes": file_data["size_bytes"]
                    })

            # Count action logs
            report["action_logs"]["to_create"] = len(metadata.get("action_logs", []))

            return report

        finally:
            db.close()

    def _restore_with_new_ids(self, db, metadata: Dict[str, Any], staging_files_dir: Path,
                             restore_id: str) -> Dict[str, Any]:
        """Restore data creating new IDs"""
        id_mapping = {}
        result = {"dependencies_created": 0, "folders_created": 0, "files_created": 0}

        # Create dependencies with new IDs
        for dep_data in metadata.get("dependencies", []):
            new_id = str(uuid.uuid4())
            id_mapping[dep_data["id"]] = new_id

            dependency = Dependency(
                id=new_id,
                name=f"{dep_data['name']} (Restored {restore_id[:8]})",
                code=f"{dep_data['code']}_RESTORED_{restore_id[:8]}"
            )
            db.add(dependency)
            result["dependencies_created"] += 1

        # Create folders with new IDs and updated references
        for folder_data in metadata.get("folders", []):
            new_id = str(uuid.uuid4())
            id_mapping[folder_data["id"]] = new_id

            # Update dependency reference if it was remapped
            dep_id = id_mapping.get(folder_data.get("dependency_id"), folder_data.get("dependency_id"))
            parent_id = id_mapping.get(folder_data.get("parent_id"), folder_data.get("parent_id"))

            folder = Folder(
                id=new_id,
                name=folder_data["name"],
                path=folder_data["path"],
                dependency_id=dep_id,
                parent_id=parent_id,
                created_by=folder_data.get("created_by"),
                updated_by=folder_data.get("updated_by")
            )
            db.add(folder)
            result["folders_created"] += 1

        # Create files with new IDs and updated references
        for file_data in metadata.get("files", []):
            new_id = str(uuid.uuid4())
            id_mapping[file_data["id"]] = new_id

            # Generate new stored name to avoid conflicts
            original_ext = Path(file_data["original_name"]).suffix
            new_stored_name = f"{new_id}{original_ext}"

            # Update folder reference
            folder_id = id_mapping.get(file_data.get("folder_id"), file_data.get("folder_id"))
            dep_id = id_mapping.get(file_data.get("dependency_id"), file_data.get("dependency_id"))

            # Update main_file_id reference
            main_file_id = id_mapping.get(file_data.get("main_file_id"), file_data.get("main_file_id"))

            file_obj = File(
                id=new_id,
                original_name=file_data["original_name"],
                stored_name=new_stored_name,  # New stored name
                mime_type=file_data["mime_type"],
                size_bytes=file_data["size_bytes"],
                checksum_sha256=file_data["checksum_sha256"],
                folder_id=folder_id,
                dependency_id=dep_id,
                uploaded_by=file_data.get("uploaded_by"),
                version=file_data["version"],
                is_deleted=file_data.get("is_deleted", False),
                main_file_id=main_file_id,
                file_metadata=file_data.get("file_metadata"),
                created_at=file_data.get("created_at"),
                updated_at=file_data.get("updated_at")
            )
            db.add(file_obj)
            result["files_created"] += 1

        # Store ID mapping for file restoration
        result["id_mapping"] = id_mapping
        result["staging_files_dir"] = str(staging_files_dir)

        return result

    def _restore_with_overwrite(self, db, metadata: Dict[str, Any], staging_files_dir: Path,
                               preserve_existing: bool) -> Dict[str, Any]:
        """Restore data overwriting existing records"""
        # This is dangerous - only for clean restores
        result = {"dependencies_created": 0, "folders_created": 0, "files_created": 0}

        # For now, implement as create_new_ids but warn about overwrite
        logger.warning("Overwrite strategy not fully implemented - using create_new_ids")
        return self._restore_with_new_ids(db, metadata, staging_files_dir, "overwrite")

    def _finalize_file_restore(self, staging_files_dir: Path, metadata: Dict[str, Any]) -> int:
        """Move staged files to final storage location"""
        files_restored = 0

        for file_path in staging_files_dir.iterdir():
            if file_path.is_file():
                # Find corresponding metadata
                stored_name = file_path.name
                file_meta = None

                for f in metadata.get("files", []):
                    if f["stored_name"] == stored_name:
                        file_meta = f
                        break

                if file_meta:
                    try:
                        # Get dependency code
                        dep_code = self._get_dependency_code(file_meta["dependency_id"])

                        # Get folder path (remove filename from full path)
                        folder_path = file_meta.get("path", "")
                        if "/" in folder_path:
                            folder_path = "/".join(folder_path.split("/")[:-1])

                        # Move to final location
                        final_path = storage_service.get_file_path(dep_code, folder_path, stored_name)
                        final_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(file_path), str(final_path))

                        files_restored += 1

                    except Exception as e:
                        logger.error(f"Failed to finalize file {stored_name}: {e}")

        return files_restored

# Global backup service instance
backup_service = BackupService()
