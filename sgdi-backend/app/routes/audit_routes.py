from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ..core.database import get_db
from ..core.auth import require_super_admin, require_admin_dep_or_super
from ..models.user import User
from ..services.audit_service import audit_service
from ..schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/logs", response_model=dict, responses={
    200: {"description": "List of audit logs with pagination"},
    403: {"model": ErrorResponse}
})
async def get_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    dependency_id: Optional[str] = Query(None, description="Filter by dependency ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    target_type: Optional[str] = Query(None, description="Filter by target type (file, folder, user, etc.)"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    format: str = Query("json", description="Response format: json, csv, or xlsx"),
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Query audit logs with advanced filtering and export options.

    - Super Admin: Can see all logs with any filters
    - Admin: Can only see logs related to their dependency
    - Supports date range filtering and pagination
    - Export formats: JSON (default), CSV, XLSX
    """
    try:
        # Parse dates
        start_date_parsed = None
        end_date_parsed = None

        if start_date:
            try:
                start_date_parsed = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
                )

        if end_date:
            try:
                end_date_parsed = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
                )

        # Handle export formats
        if format.lower() == "csv":
            return audit_service.export_audit_logs_csv(
                db=db,
                user_id=user_id,
                dependency_id=dependency_id,
                action_type=action_type,
                target_type=target_type,
                start_date=start_date_parsed,
                end_date=end_date_parsed,
                requesting_user=current_user
            )
        elif format.lower() == "xlsx":
            # TODO: Implement XLSX export
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="XLSX export not yet implemented"
            )

        # Default JSON response
        logs, total_count = audit_service.query_audit_logs(
            db=db,
            user_id=user_id,
            dependency_id=dependency_id,
            action_type=action_type,
            target_type=target_type,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
            limit=limit,
            offset=offset,
            requesting_user=current_user
        )

        return {
            "logs": logs,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=dict, responses={
    200: {"description": "User audit summary with logs and statistics"},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse}
})
async def get_user_audit_logs(
    user_id: str,
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Get audit logs for a specific user with action type statistics.

    - Super Admin: Can see logs for any user
    - Admin: Can only see logs for users in their dependency
    - Returns user's recent logs and action type counts
    """
    try:
        result = audit_service.get_user_audit_summary(db, user_id, current_user)

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=result["error"]
            )

        if not result["user"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user audit logs for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/file/{file_id}", response_model=List[dict], responses={
    200: {"description": "Chronological audit logs for file and its annexes"},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse}
})
async def get_file_audit_logs(
    file_id: str,
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Get chronological audit logs for a file and all its annexes.

    - Includes logs where target_id = file_id OR main_file_id = file_id
    - Sorted by timestamp (most recent first)
    - Permission checks based on file's dependency
    """
    try:
        logs = audit_service.get_file_audit_logs(db, file_id, current_user)

        return logs

    except Exception as e:
        logger.error(f"Error getting file audit logs for {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# Legacy endpoints for backward compatibility
@router.get("")
@router.get("/")
def read_action_logs_legacy(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Legacy endpoint for backward compatibility
    """
    logs, _ = audit_service.query_audit_logs(
        db=db,
        limit=limit,
        offset=skip,
        requesting_user=current_user
    )
    return logs

@router.get("/{action_log_id}")
async def read_action_log_legacy(
    action_log_id: str,
    current_user: User = Depends(require_admin_dep_or_super),
    db: Session = Depends(get_db)
):
    """
    Legacy endpoint for backward compatibility
    """
    from ..models.action_logs import ActionLog

    log = db.query(ActionLog).filter(ActionLog.id == action_log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action log not found"
        )

    # Check permissions (basic check - could be enhanced)
    if current_user.role != "SUPER_ADMIN" and log.user_id != current_user.id:
        # For admin, we'd need more complex permission checking
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return log
