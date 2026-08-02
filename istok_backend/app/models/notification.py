from sqlalchemy import Column, Enum as SAEnum, ForeignKey, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
import enum
from app.core.database import Base

class NotificationTypeEnum(str, enum.Enum):
    NEW_REQUEST = "new_request"
    REQUEST_APPROVED = "request_approved"
    PERSON_FOUND = "person_found"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(SAEnum(NotificationTypeEnum), nullable=False)
    payload = Column(JSONB, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)