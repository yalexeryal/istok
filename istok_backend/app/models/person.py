from sqlalchemy import Column, String, Date, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import date
import enum
from app.core.database import Base

class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"

class Person(Base):
    __tablename__ = "persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    birth_place = Column(String, nullable=True)
    death_date = Column(Date, nullable=True)
    death_place = Column(String, nullable=True)
    gender = Column(SAEnum(GenderEnum), nullable=True)
    photo_url = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)