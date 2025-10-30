from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
import logging
import uuid

from ..core.database import SessionLocal
from ..core.config import settings
from ..models.dependency import Dependency
from ..models.folder import Folder
from ..models.user import User
from ..services.audit_service import audit_service

logger = logging.getLogger(__name__)

def create_monthly_folders_for_month(target_year: int = None, target_month: int = None):
    """
    Create monthly folders for all active dependencies for a specific month.

    Args:
        target_year: Year to create folders for (default: current year)
        target_month: Month to create folders for (default: current month)

    Returns:
        List of created folder dictionaries
    """
    if target_year is None or target_month is None:
        now = datetime.utcnow()
        target_year = now.year
        target_month = now.month

    logger.info(f"Creating monthly folders for {target_year}-{target_month:02d}")

    db = SessionLocal()
    created_folders = []

    try:
        # Get system user for audit logging
        system_user = db.query(User).filter(User.id == settings.system_user_id).first()
        if not system_user:
            logger.error(f"System user {settings.system_user_id} not found")
            return []

        # Get all dependencies (Dependency model doesn't have is_active field)
        dependencies = db.query(Dependency).all()

        for dependency in dependencies:
            try:
                # Find root folder for this dependency (parent_id is None)
                root_folder = db.query(Folder).filter(
                    Folder.dependency_id == dependency.id,
                    Folder.parent_id.is_(None)
                ).first()

                if not root_folder:
                    logger.warning(f"No root folder found for dependency {dependency.code}, skipping")
                    continue

                # Generate folder name: YYYY-MM
                folder_name = f"{target_year}-{target_month:02d}"

                # Check if folder already exists (idempotency)
                existing_folder = db.query(Folder).filter(
                    Folder.dependency_id == dependency.id,
                    Folder.parent_id == root_folder.id,
                    Folder.name == folder_name
                ).first()

                if existing_folder:
                    logger.debug(f"Folder {folder_name} already exists for dependency {dependency.code}")
                    continue

                # Create folder path relative to root
                folder_path = f"{root_folder.path}/{folder_name}"

                # Create folder record with explicit UUID
                folder = Folder(
                    id=str(uuid.uuid4()),
                    name=folder_name,
                    path=folder_path,
                    parent_id=root_folder.id,
                    dependency_id=dependency.id,
                    created_by=settings.system_user_id,
                    updated_by=settings.system_user_id
                )

                db.add(folder)
                db.flush()  # Get the ID

                # Create physical directory if storage is configured
                if hasattr(settings, 'storage_path') and settings.storage_path:
                    try:
                        # Convert dependency code to safe path component
                        safe_dep_code = dependency.code.replace('/', '_').replace('\\', '_')
                        full_path = Path(settings.storage_path) / "dependencies" / safe_dep_code / folder_path
                        full_path.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        logger.warning(f"Failed to create physical directory for {folder_path}: {e}")

                # Log audit event (disabled to avoid transaction conflicts)
                # TODO: Re-enable audit logging after fixing transaction handling
                # audit_service.log_action(
                #     db=db,
                #     user=system_user,
                #     action_type="CREATE_FOLDER",
                #     target_type="FOLDER",
                #     target_id=folder.id,
                #     details={
                #         "name": folder.name,
                #         "path": folder.path,
                #         "dependency_id": dependency.id,
                #         "is_monthly": True,
                #         "year": target_year,
                #         "month": target_month
                #     }
                # )

                created_folders.append({
                    "id": folder.id,
                    "name": folder.name,
                    "path": folder.path,
                    "dependency_id": dependency.id,
                    "dependency_code": dependency.code,
                    "dependency_name": dependency.name
                })

                logger.info(f"Created monthly folder: {folder_path} for dependency {dependency.code}")

            except Exception as e:
                logger.error(f"Error creating folder for dependency {dependency.code}: {e}")
                continue

        db.commit()
        logger.info(f"Monthly folders creation completed. Created {len(created_folders)} folders.")

    except Exception as e:
        logger.error(f"Error in monthly folders creation: {e}")
        db.rollback()
        created_folders = []
    finally:
        db.close()

    return created_folders

def create_monthly_folders():
    """
    Create monthly folders for current month.
    This is the scheduled job function.
    """
    return create_monthly_folders_for_month()

def scheduled_monthly_folders():
    """
    Wrapper function for APScheduler to call monthly folder creation.
    """
    try:
        create_monthly_folders()
    except Exception as e:
        logger.error(f"Scheduled monthly folders task failed: {e}")
        raise

def cleanup_old_folders(retention_years: int = 7):
    """
    Mark old folders as inactive based on retention policy.
    This helps manage database size and cleanup old records.

    Args:
        retention_years: Number of years to keep folders active
    """
    logger.info(f"Starting cleanup of folders older than {retention_years} years")

    db = SessionLocal()
    try:
        # Get system user for audit logging
        system_user = db.query(User).filter(User.id == settings.system_user_id).first()
        if not system_user:
            logger.error(f"System user {settings.system_user_id} not found")
            return

        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=retention_years * 365)

        # Find folders to cleanup (system folders without retention period set)
        # Note: Folder model doesn't have is_system, is_active, or retention_period_years fields
        # This cleanup function is not currently functional and needs schema updates
        old_folders = []

        folders_deactivated = 0

        for folder in old_folders:
            try:
                folder.is_active = False
                folder.updated_by = settings.system_user_id

                # Log audit event
                audit_service.log_system_action(
                    db=db,
                    user=system_user,
                    action="FOLDER_UPDATE",
                    description=f"Folder deactivated due to retention policy: {folder.path}"
                )

                folders_deactivated += 1
                logger.info(f"Deactivated old folder: {folder.path}")

            except Exception as e:
                logger.error(f"Error deactivating folder {folder.path}: {e}")
                continue

        db.commit()
        logger.info(f"Folder cleanup completed. Deactivated {folders_deactivated} folders.")

    except Exception as e:
        logger.error(f"Error in folder cleanup: {e}")
        db.rollback()
    finally:
        db.close()

def get_next_month_info() -> dict:
    """
    Get information about the next month for folder creation.

    Returns:
        Dictionary with year, month, and folder name
    """
    today = datetime.utcnow().date()

    # Determine target month
    if today.day > 15:
        # Create for next month
        target_date = today.replace(day=1) + timedelta(days=32)
        target_date = target_date.replace(day=1)
    else:
        # Create for current month
        target_date = today.replace(day=1)

    return {
        "year": target_date.year,
        "month": target_date.month,
        "folder_name": generate_folder_name(target_date.year, target_date.month),
        "target_date": target_date.isoformat()
    }

# Function to be called by scheduler
def scheduled_monthly_folders():
    """
    Wrapper function for scheduler to call monthly folder creation
    """
    try:
        create_monthly_folders()
        # Optional: cleanup old folders
        cleanup_old_folders()
    except Exception as e:
        logger.error(f"Scheduled monthly folders task failed: {e}")

if __name__ == "__main__":
    # Allow running as standalone script
    create_monthly_folders()
