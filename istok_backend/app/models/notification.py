import enum
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSON
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class NotificationTypeEnum(str, enum.Enum):
    NEW_REQUEST = "new_request"
    REQUEST_APPROVED = "request_approved"
    REQUEST_REJECTED = "request_rejected"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Тип уведомления
    type = Column(ENUM(NotificationTypeEnum, name="notificationtypeenum", create_type=False), nullable=False)

    # Текст уведомления
    message = Column(String(500), nullable=False)

    # Дополнительные данные в формате JSON (опционально)
    payload = Column(JSON, nullable=True)

    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())