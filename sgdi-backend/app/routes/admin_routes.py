from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from ..core.database import get_db
from ..core.auth import require_super_admin
from ..models.user import User
from ..schemas.common import ErrorResponse
from ..tasks.monthly_folders import create_monthly_folders_for_month

logger = logging.getLogger(__name__)

router = APIRouter()

class MonthlyFolderResponse:
    """Response model for monthly folder creation"""
    def __init__(self, folders_created: List[dict]):
        self.folders_created = folders_created

@router.post("/force-create-month-folders", response_model=dict, responses={
    200: {"description": "Monthly folders created successfully"},
    403: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def force_create_monthly_folders(
    month: Optional[str] = Query(None, description="Month in YYYY-MM format (default: current month)"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Manually trigger monthly folder creation for all dependencies.

    - Super admin only
    - Optional month parameter (default: current month)
    - Returns list of created folders
    """
    try:
        # Parse month parameter
        target_year = None
        target_month = None

        if month:
            try:
                year, month_num = month.split('-')
                target_year = int(year)
                target_month = int(month_num)

                # Validate month range
                if not (1 <= target_month <= 12):
                    raise ValueError("Invalid month")

                # Validate year is reasonable
                current_year = datetime.utcnow().year
                if not (current_year - 1 <= target_year <= current_year + 1):
                    raise ValueError("Year out of reasonable range")

            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid month format. Use YYYY-MM (e.g., 2024-12)"
                )

        logger.info(f"Manual monthly folder creation triggered by {current_user.email} for month {month or 'current'}")

        # Execute folder creation
        created_folders = create_monthly_folders_for_month(target_year, target_month)

        return {
            "success": True,
            "message": f"Monthly folders creation completed. Created {len(created_folders)} folders.",
            "folders_created": created_folders,
            "target_month": month or f"{datetime.utcnow().year}-{datetime.utcnow().month:02d}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual monthly folder creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during folder creation: {str(e)}"
        )
