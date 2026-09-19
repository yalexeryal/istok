"""
Модели данных SQLAlchemy для системы "Исток".
Включает модели для персон, событий, связей, деревьев и прав доступа.
"""
import enum
from sqlalchemy import Column, Integer, String, Text, Date, Boolean, ForeignKey, Enum as SAEnum, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# --- ENUMS (Перечисления) ---

class GenderEnum(str, enum.Enum):
    """Пол персоны."""
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class EventTypeEnum(str, enum.Enum):
    """Типы событий жизни."""
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
    """Типы родственных связей."""
    BIOLOGICAL_PARENT = "biological_parent"
    ADOPTIVE_PARENT = "adoptive_parent"
    STEP_PARENT = "step_parent"
    SPOUSE = "spouse"
    EX_SPOUSE = "ex_spouse"
    FIANCE = "fiance"
    GUARDIAN = "guardian"
    GODPARENT = "godparent"


class CollaboratorRoleEnum(str, enum.Enum):
    """Роли соавторов дерева."""
    OWNER = "owner"
    CO_EDITOR = "co_editor"
    EDITOR = "editor"
    VIEWER = "viewer"


class ChangeRequestStatusEnum(str, enum.Enum):
    """Статусы запросов на изменения."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


# --- MODELS (Модели) ---

class User(Base):
    """Модель пользователя системы (редактора дерева)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Person(Base):
    """
    Модель персоны в генеалогическом дереве.
    """
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
    tree_id = Column(Integer, ForeignKey('trees.id'), nullable=False, default=1, index=True)
    status = Column(String(20), nullable=False, default="sandbox", index=True)
    merged_into_id = Column(Integer, ForeignKey('persons.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    life_events = relationship("LifeEvent", back_populates="person", cascade="all, delete-orphan",
                               foreign_keys="LifeEvent.person_id")
    updater = relationship("User", foreign_keys=[updated_by_id])
    merged_into = relationship("Person", remote_side=[id], foreign_keys=[merged_into_id])
    tree = relationship("Tree", back_populates="persons")

    @property
    def full_name_display(self) -> str:
        """Формирует красивое полное имя для отображения."""
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
    """Модель события жизни персоны (хронология)."""
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
    """Модель связи между двумя персонами."""
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


class Tree(Base):
    """Модель генеалогического дерева."""
    __tablename__ = "trees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    collaborators = relationship("TreeCollaborator", back_populates="tree", cascade="all, delete-orphan")
    persons = relationship("Person", back_populates="tree", cascade="all, delete-orphan")


class TreeCollaborator(Base):
    """Модель соавтора дерева (права доступа)."""
    __tablename__ = "tree_collaborators"

    id = Column(Integer, primary_key=True, index=True)
    tree_id = Column(Integer, ForeignKey('trees.id', ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SAEnum(CollaboratorRoleEnum), nullable=False, default=CollaboratorRoleEnum.VIEWER)
    can_invite = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    tree = relationship("Tree", back_populates="collaborators")
    user = relationship("User")


class ChangeRequest(Base):
    """Модель запроса на изменение персоны."""
    __tablename__ = "change_requests"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey('persons.id', ondelete="CASCADE"), nullable=False, index=True)
    requested_by_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    change_type = Column(String(50), nullable=False)  # create/update/delete
    proposed_data = Column(JSON, nullable=True)
    status = Column(SAEnum(ChangeRequestStatusEnum), nullable=False, default=ChangeRequestStatusEnum.PENDING)
    created_at = Column(DateTime, server_default=func.now())
    responded_at = Column(DateTime, nullable=True)
    response_comment = Column(Text, nullable=True)

    person = relationship("Person")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    owner = relationship("User", foreign_keys=[owner_id])