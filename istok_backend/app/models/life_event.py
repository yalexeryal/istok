from sqlalchemy import Column, String, Date, Boolean, Text, Enum as SAEnum, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import date, datetime
import enum
from app.core.database import Base

class EventTypeEnum(str, enum.Enum):
    BIRTH = "birth"
    DEATH = "death"
    MARRIAGE = "marriage"
    CHILD_BIRTH = "child_birth"
    EDUCATION = "education"
    MILITARY_SERVICE = "military_service"
    WORK = "work"
    RELOCATION = "relocation"
    AWARD = "award"
    OTHER = "other"

class EventSourceEnum(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"

class LifeEvent(Base):
    __tablename__ = "life_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id"), nullable=False)
    event_type = Column(SAEnum(EventTypeEnum), nullable=False)
    date = Column(Date, nullable=True)
    date_approx = Column(Boolean, default=False)
    place = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    source = Column(SAEnum(EventSourceEnum), default=EventSourceEnum.MANUAL)
    created_at = Column(DateTime, default=datetime.utcnow)