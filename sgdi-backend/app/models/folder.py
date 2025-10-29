from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from ..core.database import Base

class Folder(Base):
    __tablename__ = "folders"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(String, ForeignKey("folders.id"))
    dependency_id = Column(String, ForeignKey("dependencies.id"), nullable=False)
    created_by = Column(String, ForeignKey("users.id"))
    path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Folder(id={self.id}, name={self.name}, path={self.path})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "dependency_id": self.dependency_id,
            "created_by": self.created_by,
            "path": self.path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
