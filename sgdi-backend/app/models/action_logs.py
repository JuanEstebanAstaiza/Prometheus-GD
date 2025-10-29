from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from ..core.database import Base

class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    user_role = Column(String)
    action_type = Column(String, nullable=False)
    target_type = Column(String)
    target_id = Column(String)
    details = Column(JSON)
    ip_address = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ActionLog(id={self.id}, action_type={self.action_type}, user_id={self.user_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_role": self.user_role,
            "action_type": self.action_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
