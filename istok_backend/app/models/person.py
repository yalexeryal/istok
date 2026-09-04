from sqlalchemy import Column, Enum as SAEnum, String, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.core.database import Base


class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class Person(Base):
    __tablename__ = "persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    birth_date = Column(Date, nullable=True)
    birth_place = Column(String(200), nullable=True)
    death_date = Column(Date, nullable=True)
    death_place = Column(String(200), nullable=True)
    burial_place = Column(String(200), nullable=True)  # Новое поле: место погребения
    gender = Column(SAEnum(GenderEnum), nullable=True)
    photo_url = Column(String(500), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    def __repr__(self):
        return f"<Person {self.first_name} {self.last_name}>"