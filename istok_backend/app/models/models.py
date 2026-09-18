import enum
from sqlalchemy import Column, Integer, String, Text, Date, Boolean, ForeignKey, Enum as SAEnum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class EventTypeEnum(str, enum.Enum):
    BIRTH = "birth"
    DEATH = "death"
    MARRIAGE = "marriage"
    DIVORCE = "divorce"
    BIRTH_OF_CHILD = "birth_of_child"
    EDUCATION = "education"
    WORK = "work"
    MILITARY_SERVICE = "military"
    MIGRATION = "migration"
    RELIGIOUS_EVENT = "religious_event"
    OTHER = "other"


class RelationshipTypeEnum(str, enum.Enum):
    BIOLOGICAL_PARENT = "biological_parent"
    ADOPTIVE_PARENT = "adoptive_parent"
    STEP_PARENT = "step_parent"
    SPOUSE = "spouse"
    EX_SPOUSE = "ex_spouse"
    FIANCE = "fiance"
    GUARDIAN = "guardian"
    GODPARENT = "godparent"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False, index=True)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True, index=True)
    maiden_name = Column(String(100), nullable=True)
    birth_date = Column(Date, nullable=True)
    is_birth_date_approx = Column(Boolean, default=False)
    death_date = Column(Date, nullable=True)
    is_death_date_approx = Column(Boolean, default=False)
    birth_place = Column(String(255), nullable=True)
    death_place = Column(String(255), nullable=True)
    burial_place = Column(String(255), nullable=True)
    gender = Column(SAEnum(GenderEnum), nullable=True)
    culture = Column(String(50), nullable=True)
    photo_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    tree_id = Column(Integer, nullable=False, default=1, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    life_events = relationship("LifeEvent", back_populates="person", cascade="all, delete-orphan",
                               foreign_keys="LifeEvent.person_id")
    updater = relationship("User", foreign_keys=[updated_by_id])
    @property
    def full_name_display(self) -> str:
        parts = []
        if self.maiden_name and self.gender == GenderEnum.FEMALE:
            parts.append(f"{self.last_name} ({self.maiden_name})")
        elif self.last_name:
            parts.append(self.last_name)
        parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)


class LifeEvent(Base):
    __tablename__ = "life_events"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey('persons.id', ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(SAEnum(EventTypeEnum), nullable=False, index=True)
    event_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_date_approx = Column(Boolean, default=False)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    related_person_id = Column(Integer, ForeignKey('persons.id', ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    person = relationship("Person", back_populates="life_events", foreign_keys=[person_id])
    related_person = relationship("Person", foreign_keys=[related_person_id])
    creator = relationship("User", foreign_keys=[created_by_id])


class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(Integer, primary_key=True, index=True)
    from_person_id = Column(Integer, ForeignKey('persons.id', ondelete="CASCADE"), nullable=False, index=True)
    to_person_id = Column(Integer, ForeignKey('persons.id', ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(SAEnum(RelationshipTypeEnum), nullable=False, index=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    from_person = relationship("Person", foreign_keys=[from_person_id])
    to_person = relationship("Person", foreign_keys=[to_person_id])
    creator = relationship("User", foreign_keys=[created_by_id])