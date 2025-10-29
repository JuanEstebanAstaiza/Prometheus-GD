from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from typing import Optional, Dict, Any, List, Tuple
import logging
import csv
import io
from datetime import datetime, date
from fastapi.responses import StreamingResponse

from ..models.action_logs import ActionLog
from ..models.user import User
from ..models.dependency import Dependency
from ..models.folder import Folder
from ..models.file import File

logger = logging.getLogger(__name__)

class AuditService:
    """Service for managing audit logging"""

    @staticmethod
    def log_action(
        db: Session,
        user: User,
        action_type: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        action_log_id: Optional[str] = None
    ) -> ActionLog:
        """
        Create an action log entry

        Args:
            db: Database session
            user: User performing the action
            action_type: Type of action performed
            target_type: Type of target (optional)
            target_id: ID of the target (optional)
            details: Additional details as JSON
            ip_address: Client IP address
            action_log_id: Specific ID for the log entry (optional)

        Returns:
            Created action log entry
        """
        try:
            action_log = ActionLog(
                id=action_log_id,
                user_id=user.id,
                user_role=user.role,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                details=details,
                ip_address=ip_address
            )

            db.add(action_log)
            db.commit()
            db.refresh(action_log)

            logger.info(f"Action logged: {action_type} by user {user.email}")
            return action_log

        except Exception as e:
            logger.error(f"Failed to create action log: {e}")
            db.rollback()
            raise e

    @staticmethod
    def log_user_action(
        db: Session,
        user: User,
        action_type: str,
        target_user: User,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ActionLog:
        """Log an action performed on a user"""
        return AuditService.log_action(
            db=db,
            user=user,
            action_type=action_type,
            target_type="user",
            target_id=target_user.id,
            details=details,
            **kwargs
        )

    @staticmethod
    def log_file_action(
        db: Session,
        user: User,
        action_type: str,
        file_id: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ActionLog:
        """Log an action performed on a file"""
        return AuditService.log_action(
            db=db,
            user=user,
            action_type=action_type,
            target_type="file",
            target_id=file_id,
            details=details,
            **kwargs
        )

    @staticmethod
    def log_folder_action(
        db: Session,
        user: User,
        action_type: str,
        folder_id: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ActionLog:
        """Log an action performed on a folder"""
        return AuditService.log_action(
            db=db,
            user=user,
            action_type=action_type,
            target_type="folder",
            target_id=folder_id,
            details=details,
            **kwargs
        )

    @staticmethod
    def get_action_logs(
        db: Session,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        Get action logs with optional filters

        Args:
            db: Database session
            user_id: Filter by user ID
            action_type: Filter by action type
            target_type: Filter by target type
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of action log entries
        """
        query = db.query(ActionLog).order_by(ActionLog.timestamp.desc())

        if user_id:
            query = query.filter(ActionLog.user_id == user_id)
        if action_type:
            query = query.filter(ActionLog.action_type == action_type)
        if target_type:
            query = query.filter(ActionLog.target_type == target_type)

        return query.offset(offset).limit(limit).all()

    @staticmethod
    def query_audit_logs(
        db: Session,
        user_id: Optional[str] = None,
        dependency_id: Optional[str] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        requesting_user: Optional[User] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Query audit logs with advanced filtering and permission checks

        Args:
            db: Database session
            user_id: Filter by user ID
            dependency_id: Filter by dependency ID
            action_type: Filter by action type
            target_type: Filter by target type
            start_date: Filter from date
            end_date: Filter to date
            limit: Maximum records to return
            offset: Records to skip
            requesting_user: User making the request (for permission filtering)

        Returns:
            Tuple of (logs_list, total_count)
        """
        from sqlalchemy import text

        # Base query with joins to get user information
        query = db.query(
            ActionLog,
            User.full_name.label('user_full_name'),
            User.role.label('user_role')
        ).join(
            User, ActionLog.user_id == User.id
        ).order_by(ActionLog.timestamp.desc())

        # Apply filters
        if user_id:
            query = query.filter(ActionLog.user_id == user_id)

        if action_type:
            query = query.filter(ActionLog.action_type == action_type)

        if target_type:
            query = query.filter(ActionLog.target_type == target_type)

        if start_date:
            query = query.filter(ActionLog.timestamp >= start_date)

        if end_date:
            query = query.filter(ActionLog.timestamp <= end_date)

        # Apply permission-based filtering
        if requesting_user and requesting_user.role != "SUPER_ADMIN":
            # Admin can only see logs for their dependency
            if requesting_user.dependency_id:
                # Complex filtering for dependency-related logs
                # This includes logs where the dependency_id is explicitly mentioned
                # or can be inferred from related entities
                dependency_filter = text(f"""
                    (action_log.details->>'dependency_id' = :dep_id) OR
                    (action_log.target_type = 'folder' AND EXISTS (
                        SELECT 1 FROM folders f WHERE f.id = action_log.target_id
                        AND f.dependency_id = :dep_id
                    )) OR
                    (action_log.target_type = 'file' AND EXISTS (
                        SELECT 1 FROM files f WHERE f.id = action_log.target_id
                        AND f.dependency_id = :dep_id
                    )) OR
                    (action_log.details->>'main_file_id' IS NOT NULL AND EXISTS (
                        SELECT 1 FROM files f WHERE f.id = (action_log.details->>'main_file_id')
                        AND f.dependency_id = :dep_id
                    ))
                """)

                query = query.filter(dependency_filter).params(dep_id=requesting_user.dependency_id)
            else:
                # User without dependency can't see any logs
                return [], 0

        # Get total count
        count_query = query.with_entities(func.count(ActionLog.id))
        total_count = count_query.scalar()

        # Apply pagination and get results
        results = query.offset(offset).limit(limit).all()

        # Format results with summaries
        logs = []
        for log_entry, user_full_name, user_role in results:
            log_data = {
                "timestamp": log_entry.timestamp.isoformat() if log_entry.timestamp else None,
                "user_id": log_entry.user_id,
                "user_full_name": user_full_name,
                "user_role": user_role,
                "action_type": log_entry.action_type,
                "target_type": log_entry.target_type,
                "target_id": log_entry.target_id,
                "summary": AuditService.generate_summary(log_entry, user_full_name),
                "details": log_entry.details,
                "ip_address": log_entry.ip_address
            }
            logs.append(log_data)

        return logs, total_count

    @staticmethod
    def generate_summary(log_entry: ActionLog, user_full_name: str) -> str:
        """
        Generate a human-readable summary for an audit log entry

        Args:
            log_entry: The action log entry
            user_full_name: Full name of the user who performed the action

        Returns:
            Human-readable summary string
        """
        action_type = log_entry.action_type
        details = log_entry.details or {}
        target_type = log_entry.target_type

        # Action-specific summary templates
        templates = {
            "LOGIN": f"{user_full_name} inició sesión",
            "LOGOUT": f"{user_full_name} cerró sesión",
            "LOGIN_FAILURE": f"Falló intento de inicio de sesión para {user_full_name}",
            "TOKEN_REFRESH": f"{user_full_name} renovó su token de acceso",

            "CREATE_USER": f"{user_full_name} creó un nuevo usuario: {details.get('email', 'N/A')}",
            "UPDATE_USER": f"{user_full_name} actualizó información de usuario",
            "DELETE_USER": f"{user_full_name} eliminó un usuario",

            "CREATE_DEPENDENCY": f"{user_full_name} creó la dependencia: {details.get('name', 'N/A')}",
            "UPDATE_DEPENDENCY": f"{user_full_name} actualizó la dependencia: {details.get('name', 'N/A')}",
            "DELETE_DEPENDENCY": f"{user_full_name} eliminó la dependencia: {details.get('name', 'N/A')}",

            "CREATE_FOLDER": AuditService._generate_folder_create_summary(user_full_name, details),
            "UPDATE_FOLDER": AuditService._generate_folder_update_summary(user_full_name, details),
            "DELETE_FOLDER": AuditService._generate_folder_delete_summary(user_full_name, details),

            "UPLOAD": AuditService._generate_upload_summary(user_full_name, details),
            "DOWNLOAD": AuditService._generate_download_summary(user_full_name, details),
            "UPDATE": AuditService._generate_update_summary(user_full_name, details),
            "DELETE": AuditService._generate_delete_summary(user_full_name, details),

            "RESTORE": f"{user_full_name} ejecutó una restauración del sistema",
            "BACKUP_CREATE": f"{user_full_name} creó un backup del sistema",

            "FOLDER_CREATE": f"{user_full_name} creó una carpeta del sistema: {details.get('name', 'N/A')}",
            "FOLDER_UPDATE": f"{user_full_name} actualizó una carpeta del sistema",
            "FOLDER_DELETE": f"{user_full_name} eliminó una carpeta del sistema"
        }

        return templates.get(action_type, f"{user_full_name} realizó la acción: {action_type}")

    @staticmethod
    def _generate_folder_create_summary(user_full_name: str, details: Dict[str, Any]) -> str:
        """Generate summary for folder creation"""
        folder_name = details.get('name', 'N/A')
        purpose = details.get('purpose')

        if purpose == 'annex_folder':
            main_file = details.get('main_file', 'N/A')
            return f"{user_full_name} creó carpeta de anexos '{folder_name}' para el archivo {main_file}"

        return f"{user_full_name} creó la carpeta: {folder_name}"

    @staticmethod
    def _generate_folder_update_summary(user_full_name: str, details: Dict[str, Any]) -> str:
        """Generate summary for folder update"""
        folder_name = details.get('name', details.get('path', 'N/A'))
        return f"{user_full_name} actualizó la carpeta: {folder_name}"

    @staticmethod
    def _generate_folder_delete_summary(user_full_name: str, details: Dict[str, Any]) -> str:
        """Generate summary for folder deletion"""
        folder_name = details.get('name', details.get('path', 'N/A'))
        return f"{user_full_name} eliminó la carpeta: {folder_name}"

    @staticmethod
    def _generate_upload_summary(user_full_name: str, details: Dict[str, Any]) -> str:
        """Generate summary for file upload"""
        filename = details.get('filename', details.get('original_name', 'N/A'))
        annex_count = details.get('annex_count', 0)
        folder_path = details.get('folder_path', 'N/A')

        if annex_count > 0:
            return f"{user_full_name} subió el archivo {filename} en {folder_path} (anexos: {annex_count})"
        else:
            return f"{user_full_name} subió el archivo {filename} en {folder_path}"

    @staticmethod
    def _generate_download_summary(user_full_name: str, details: Dict[str, Any]) -> str:
        """Generate summary for file download"""
        filename = details.get('filename', 'N/A')
        return f"{user_full_name} descargó el archivo: {filename}"

    @staticmethod
    def _generate_update_summary(user_full_name: str, details: Dict[str, Any]) -> str:
        """Generate summary for file update"""
        filename = details.get('filename', details.get('original_name', 'N/A'))
        new_version = details.get('new_version', 'N/A')
        return f"{user_full_name} actualizó el archivo {filename} a versión {new_version}"

    @staticmethod
    def _generate_delete_summary(user_full_name: str, details: Dict[str, Any]) -> str:
        """Generate summary for file deletion"""
        filename = details.get('filename', details.get('original_name', 'N/A'))
        hard_delete = details.get('hard_delete', False)

        if hard_delete:
            return f"{user_full_name} eliminó permanentemente el archivo: {filename}"
        else:
            return f"{user_full_name} marcó como eliminado el archivo: {filename}"

    @staticmethod
    def get_user_audit_summary(db: Session, user_id: str, requesting_user: Optional[User] = None) -> Dict[str, Any]:
        """
        Get audit logs for a specific user with action type counts

        Args:
            db: Database session
            user_id: User ID to get logs for
            requesting_user: User making the request (for permission checks)

        Returns:
            Dictionary with logs and statistics
        """
        # Check permissions
        if requesting_user and requesting_user.role != "SUPER_ADMIN":
            # Admin can only see logs for users in their dependency
            target_user = db.query(User).filter(User.id == user_id).first()
            if not target_user or target_user.dependency_id != requesting_user.dependency_id:
                return {"error": "Access denied"}

        # Get logs for the user
        logs, total_count = AuditService.query_audit_logs(
            db=db,
            user_id=user_id,
            limit=1000,  # Get more logs for summary
            requesting_user=None  # Bypass permission check since we already checked
        )

        # Get action type counts
        action_counts = db.query(
            ActionLog.action_type,
            func.count(ActionLog.id).label('count')
        ).filter(
            ActionLog.user_id == user_id
        ).group_by(ActionLog.action_type).all()

        action_stats = {action: count for action, count in action_counts}

        # Get user info
        user = db.query(User).filter(User.id == user_id).first()

        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            } if user else None,
            "logs": logs[:100],  # Return last 100 logs
            "total_logs": total_count,
            "action_counts": action_stats
        }

    @staticmethod
    def get_file_audit_logs(db: Session, file_id: str, requesting_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """
        Get chronological audit logs for a file and its annexes

        Args:
            db: Database session
            file_id: File ID to get logs for
            requesting_user: User making the request (for permission checks)

        Returns:
            List of audit log entries
        """
        # Check if file exists and get its dependency
        file_obj = db.query(File).filter(File.id == file_id).first()
        if not file_obj:
            return []

        # Check permissions
        if requesting_user and requesting_user.role != "SUPER_ADMIN":
            if file_obj.dependency_id != requesting_user.dependency_id:
                return []

        # Get logs for the main file
        main_logs, _ = AuditService.query_audit_logs(
            db=db,
            target_type="file",
            target_id=file_id,
            limit=1000,
            requesting_user=None
        )

        # Get logs for annexes (files where main_file_id = file_id)
        annex_files = db.query(File.id).filter(File.main_file_id == file_id).all()
        annex_ids = [f.id for f, in annex_files]

        annex_logs = []
        for annex_id in annex_ids:
            logs, _ = AuditService.query_audit_logs(
                db=db,
                target_type="file",
                target_id=annex_id,
                limit=1000,
                requesting_user=None
            )
            annex_logs.extend(logs)

        # Combine and sort by timestamp
        all_logs = main_logs + annex_logs
        all_logs.sort(key=lambda x: x['timestamp'] or '', reverse=True)

        return all_logs

    @staticmethod
    def export_audit_logs_csv(
        db: Session,
        user_id: Optional[str] = None,
        dependency_id: Optional[str] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        requesting_user: Optional[User] = None
    ) -> StreamingResponse:
        """
        Export audit logs as CSV stream

        Args:
            Same as query_audit_logs

        Returns:
            StreamingResponse with CSV data
        """

        def generate_csv():
            # Write CSV header
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'timestamp', 'user_id', 'user_full_name', 'user_role',
                'action_type', 'target_type', 'target_id', 'summary', 'details', 'ip_address'
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

            # Stream data in chunks
            offset = 0
            chunk_size = 1000

            while True:
                logs, _ = AuditService.query_audit_logs(
                    db=db,
                    user_id=user_id,
                    dependency_id=dependency_id,
                    action_type=action_type,
                    target_type=target_type,
                    start_date=start_date,
                    end_date=end_date,
                    limit=chunk_size,
                    offset=offset,
                    requesting_user=requesting_user
                )

                if not logs:
                    break

                for log in logs:
                    # Convert details dict to JSON string
                    details_str = str(log['details']) if log['details'] else ''

                    writer.writerow([
                        log['timestamp'] or '',
                        log['user_id'] or '',
                        log['user_full_name'] or '',
                        log['user_role'] or '',
                        log['action_type'] or '',
                        log['target_type'] or '',
                        log['target_id'] or '',
                        log['summary'] or '',
                        details_str,
                        log['ip_address'] or ''
                    ])

                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

                offset += chunk_size

                # Safety limit
                if offset > 100000:  # Max 100k records
                    break

        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_logs_{timestamp}.csv"

        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    @staticmethod
    def log_system_action(
        db: Session,
        user: User,
        action: str,
        description: str
    ) -> ActionLog:
        """
        Log a system-level action (for scheduled tasks, etc.)

        Args:
            db: Database session
            user: System user (usually SYSTEM_USER_ID)
            action: Action type
            description: Human-readable description

        Returns:
            Created action log
        """
        return AuditService.log_action(
            db=db,
            user=user,
            action_type=action,
            target_type="system",
            target_id="system",
            details={"description": description}
        )

# Global audit service instance
audit_service = AuditService()
