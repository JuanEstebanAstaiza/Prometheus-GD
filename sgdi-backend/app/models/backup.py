from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey, JSON
from sqlalchemy.sql import func
import uuid

from ..core.database import Base

class BackupRecord(Base):
    __tablename__ = "backup_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String)
    backup_type = Column(String)  # comprehensive or dependency-specific
    dependency_id = Column(String, nullable=True)  # For dependency-specific backups
    total_files = Column(BigInteger, nullable=True)  # Total number of files in backup
    total_size_bytes = Column(BigInteger, nullable=True)  # Total size of backup in bytes
    created_by = Column(String, ForeignKey("users.id"))
    size_bytes = Column(BigInteger)
    checksum_sha256 = Column(String)
    backup_metadata = Column(JSON, nullable=True)  # Backup metadata as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<BackupRecord(id={self.id}, filename={self.filename})>"

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "backup_type": self.backup_type,
            "dependency_id": self.dependency_id,
            "total_files": self.total_files,
            "total_size_bytes": self.total_size_bytes,
            "created_by": self.created_by,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "backup_metadata": self.backup_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
