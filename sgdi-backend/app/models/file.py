from sqlalchemy import Column, String, Boolean, DateTime, Integer, BigInteger, ForeignKey, JSON
from sqlalchemy.sql import func

from ..core.database import Base

class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True)
    original_name = Column(String, nullable=False)
    stored_name = Column(String, nullable=False, unique=True)
    mime_type = Column(String)
    size_bytes = Column(BigInteger)
    checksum_sha256 = Column(String)
    folder_id = Column(String, ForeignKey("folders.id"), nullable=False)
    dependency_id = Column(String, ForeignKey("dependencies.id"), nullable=False)
    uploaded_by = Column(String, ForeignKey("users.id"))
    version = Column(Integer, default=1)
    is_deleted = Column(Boolean, default=False)
    main_file_id = Column(String, ForeignKey("files.id"))
    file_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<File(id={self.id}, original_name={self.original_name}, stored_name={self.stored_name})>"

    def to_dict(self):
        return {
            "id": self.id,
            "original_name": self.original_name,
            "stored_name": self.stored_name,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "folder_id": self.folder_id,
            "dependency_id": self.dependency_id,
            "uploaded_by": self.uploaded_by,
            "version": self.version,
            "is_deleted": self.is_deleted,
            "main_file_id": self.main_file_id,
            "file_metadata": self.file_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
