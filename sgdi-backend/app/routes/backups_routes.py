from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File as FastAPIFile, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging

from ..core.database import get_db
from ..core.auth import require_super_admin
from ..models.user import User
from ..services.backup_service import backup_service
from ..schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/create", response_model=dict, responses={
    200: {"description": "Backup created successfully"},
    403: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def create_backup(
    dependency_id: Optional[str] = Form(None, description="Dependency ID for partial backup (optional)"),
    include_logs: bool = Form(True, description="Include action logs in backup"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Create a comprehensive backup with metadata and physical files.

    - Super admin only
    - Optional dependency_id for partial backup
    - Includes metadata.json and physical files in tar.gz archive
    - Creates backup record with checksum
    """
    try:
        logger.info(f"Backup creation requested by {current_user.email}, dependency_id: {dependency_id}")

        # Create the backup
        backup_result = backup_service.create_comprehensive_backup(
            dependency_id=dependency_id,
            include_logs=include_logs,
            created_by=current_user.id
        )

        if backup_result["status"] == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Backup creation failed: {backup_result.get('error', 'Unknown error')}"
            )

        # Return success response
        return {
            "success": True,
            "message": f"Backup created successfully: {backup_result['name']}",
            "backup": {
                "id": backup_result["record_id"],
                "name": backup_result["name"],
                "filename": backup_result["archive_path"].split("/")[-1] if "archive_path" in backup_result else None,
                "type": backup_result["type"],
                "dependency_id": backup_result["dependency_id"],
                "total_files": backup_result["total_files"],
                "total_size_bytes": backup_result["total_size_bytes"],
                "checksum_sha256": backup_result.get("checksum"),
                "created_at": backup_result["completed_at"].isoformat() if backup_result.get("completed_at") else None
            },
            "download_url": f"/admin/backups/{backup_result['record_id']}/download"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during backup creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during backup creation: {str(e)}"
        )

@router.get("/", response_model=List[dict], responses={
    200: {"description": "List of backup records"},
    403: {"model": ErrorResponse}
})
async def list_backups(
    dependency_id: Optional[str] = Query(None, description="Filter by dependency ID"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    List backup records with optional filtering.

    - Super admin only
    - Optional dependency_id filter
    - Returns backup records with download URLs
    """
    try:
        backups = backup_service.get_backup_records(dependency_id)

        # Add download URLs to each backup
        for backup in backups:
            backup["download_url"] = f"/admin/backups/{backup['id']}/download"

        return backups

    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/{backup_id}", response_model=dict, responses={
    200: {"description": "Backup record details"},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse}
})
async def get_backup(
    backup_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed backup record information.

    - Super admin only
    - Includes metadata and checksum information
    """
    try:
        backup = backup_service.get_backup_record(backup_id)

        if not backup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backup record not found"
            )

        # Add download URL
        backup["download_url"] = f"/admin/backups/{backup_id}/download"

        return backup

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backup {backup_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/{backup_id}/download", responses={
    200: {"description": "Backup file download"},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse}
})
async def download_backup(
    backup_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Download backup archive file.

    - Super admin only
    - Streams the tar.gz file with proper headers
    """
    try:
        # Get backup record
        backup = backup_service.get_backup_record(backup_id)

        if not backup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backup record not found"
            )

        # Check if file exists
        archive_path = backup_service.backup_path / backup["filename"]
        if not archive_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backup file not found on disk"
            )

        # Stream the file
        def file_iterator():
            with open(archive_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        headers = {
            "Content-Disposition": f'attachment; filename="{backup["filename"]}"',
            "Content-Type": "application/gzip",
            "X-Checksum-Sha256": backup.get("checksum_sha256", ""),
            "Content-Length": str(archive_path.stat().st_size)
        }

        return StreamingResponse(
            file_iterator(),
            media_type="application/gzip",
            headers=headers
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading backup {backup_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/restore", responses={
    200: {"description": "Restore simulation or execution report"},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def restore_backup(
    backup_file: UploadFile = FastAPIFile(..., description="Backup file to restore"),
    strategy: str = Form(..., description="Restore strategy: 'simulate', 'create_new_ids', 'overwrite'"),
    preserve_existing: bool = Form(True, description="Preserve existing data (for overwrite strategy)"),
    confirm: bool = Form(False, description="Confirm dangerous operations"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Restore from backup with specified strategy.

    - Super admin only
    - Supports simulation mode for safety
    - Multiple restore strategies
    - Transaction-safe with rollback capability

    Strategies:
    - simulate: Analyze what would be restored without making changes
    - create_new_ids: Restore with new IDs to avoid conflicts
    - overwrite: Overwrite existing data (dangerous, requires confirmation)
    """
    try:
        logger.info(f"Restore requested by {current_user.email}, strategy: {strategy}, confirm: {confirm}")

        # Validate strategy
        valid_strategies = ["simulate", "create_new_ids", "overwrite"]
        if strategy not in valid_strategies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}"
            )

        # Read backup file
        backup_content = await backup_file.read()

        if strategy == "simulate":
            # Simulation mode - analyze without making changes
            result = backup_service.simulate_restore(backup_content, backup_file.filename)

            return {
                "simulation": True,
                "strategy": "simulate",
                "restore_id": result["restore_id"],
                "backup_info": {
                    "filename": backup_file.filename,
                    "metadata_version": result["metadata_version"],
                    "created_at": result["created_at"],
                    "dependency_id": result["dependency_id"],
                    "include_logs": result["include_logs"]
                },
                "impact_report": result["report"],
                "message": "Simulation completed. Review the impact report before proceeding with actual restore."
            }

        else:
            # Actual restore
            if strategy == "overwrite" and not confirm:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Overwrite strategy requires explicit confirmation (confirm=true)"
                )

            result = backup_service.restore_backup(
                backup_content,
                backup_file.filename,
                strategy=strategy,
                preserve_existing=preserve_existing,
                confirm=confirm
            )

            if result["status"] == "failed":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Restore failed: {result.get('error', 'Unknown error')}"
                )

            # Log the restore operation
            from ..services.audit_service import audit_service
            audit_service.log_action(
                db=db,
                user=current_user,
                action_type="RESTORE",
                target_type="SYSTEM",
                target_id=result["restore_id"],
                details={
                    "strategy": strategy,
                    "preserve_existing": preserve_existing,
                    "files_restored": result.get("files_restored", 0),
                    "folders_created": result.get("folders_created", 0),
                    "dependencies_created": result.get("dependencies_created", 0),
                    "backup_filename": backup_file.filename
                }
            )

            return {
                "success": True,
                "simulation": False,
                "strategy": strategy,
                "restore_id": result["restore_id"],
                "status": result["status"],
                "started_at": result["started_at"].isoformat() if result.get("started_at") else None,
                "completed_at": result["completed_at"].isoformat() if result.get("completed_at") else None,
                "summary": {
                    "dependencies_created": result.get("dependencies_created", 0),
                    "folders_created": result.get("folders_created", 0),
                    "files_restored": result.get("files_restored", 0)
                },
                "message": f"Restore completed successfully using {strategy} strategy"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during restore: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during restore: {str(e)}"
        )
