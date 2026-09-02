import enum
from sqlalchemy import Column, String, Date, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

class EventTypeEnum(str, enum.Enum):
    BIRTH = "birth"
    DEATH = "death"
    MARRIAGE = "marriage"
    DIVORCE = "divorce"
    CHILD_BIRTH = "child_birth"  # <--- ДОЛЖНО БЫТЬ ИМЕННО ТАК
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
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    
    # Используем ENUM из SQLAlchemy
    event_type = Column(ENUM(EventTypeEnum, name="eventtypeenum", create_type=False), nullable=False)
    
    date = Column(Date, nullable=True)
    date_approx = Column(Boolean, default=False, nullable=False)
    place = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    source = Column(ENUM(EventSourceEnum, name="eventsourceenum", create_type=False), nullable=False, default=EventSourceEnum.MANUAL)
    created_at = Column(DateTime(timezone=True), server_default=func.now())