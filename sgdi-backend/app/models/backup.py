from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey
from sqlalchemy.sql import func

from ..core.database import Base

class BackupRecord(Base):
    __tablename__ = "backup_records"

    id = Column(String, primary_key=True)
    filename = Column(String)
    created_by = Column(String, ForeignKey("users.id"))
    size_bytes = Column(BigInteger)
    checksum_sha256 = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<BackupRecord(id={self.id}, filename={self.filename})>"

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "created_by": self.created_by,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
