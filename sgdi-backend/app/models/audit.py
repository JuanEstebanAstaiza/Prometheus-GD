from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..core.database import Base

class Audit(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Who performed the action
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # What action was performed
    action = Column(String(100), nullable=False, index=True)  # CREATE, UPDATE, DELETE, VIEW, DOWNLOAD, etc.
    resource_type = Column(String(50), nullable=False, index=True)  # user, folder, file, dependency, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Additional context
    description = Column(Text)
    old_values = Column(JSON)  # Previous state (for updates)
    new_values = Column(JSON)  # New state (for creates/updates)
    metadata = Column(JSON)  # Additional metadata (IP, user agent, etc.)

    # System information
    ip_address = Column(String(45))  # IPv4/IPv6
    user_agent = Column(Text)
    session_id = Column(String(255))

    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<Audit(id={self.id}, action={self.action}, resource_type={self.resource_type}, user_id={self.user_id})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": str(self.user_id),
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id),
            "description": self.description,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "success": self.success,
            "error_message": self.error_message,
        }

# Common audit actions
AUDIT_ACTIONS = {
    # User actions
    "USER_LOGIN": "User login",
    "USER_LOGOUT": "User logout",
    "USER_CREATE": "User created",
    "USER_UPDATE": "User updated",
    "USER_DELETE": "User deleted",
    "USER_ACTIVATE": "User activated",
    "USER_DEACTIVATE": "User deactivated",

    # File actions
    "FILE_UPLOAD": "File uploaded",
    "FILE_DOWNLOAD": "File downloaded",
    "FILE_VIEW": "File viewed",
    "FILE_UPDATE": "File updated",
    "FILE_DELETE": "File deleted",
    "FILE_MOVE": "File moved",
    "FILE_COPY": "File copied",
    "FILE_ARCHIVE": "File archived",
    "FILE_RESTORE": "File restored",

    # Folder actions
    "FOLDER_CREATE": "Folder created",
    "FOLDER_UPDATE": "Folder updated",
    "FOLDER_DELETE": "Folder deleted",
    "FOLDER_MOVE": "Folder moved",

    # Dependency actions
    "DEPENDENCY_CREATE": "Dependency created",
    "DEPENDENCY_UPDATE": "Dependency updated",
    "DEPENDENCY_DELETE": "Dependency deleted",

    # System actions
    "SYSTEM_BACKUP": "System backup created",
    "SYSTEM_MAINTENANCE": "System maintenance performed",
}
