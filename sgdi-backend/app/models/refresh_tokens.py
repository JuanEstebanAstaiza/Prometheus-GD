from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
import uuid

from ..core.database import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    ip_address = Column(String)
    user_agent = Column(Text)

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.revoked})>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked": self.revoked,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        from datetime import datetime
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not revoked and not expired)"""
        return not self.revoked and not self.is_expired
