from sqlalchemy import Column, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.core.database import Base

class RelationTypeEnum(str, enum.Enum):
    PARENT_CHILD = "parent_child"
    SPOUSE = "spouse"
    SIBLING = "sibling"

class Relation(Base):
    __tablename__ = "relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_1_id = Column(UUID(as_uuid=True), ForeignKey("persons.id"), nullable=False)
    person_2_id = Column(UUID(as_uuid=True), ForeignKey("persons.id"), nullable=False)
    type = Column(SAEnum(RelationTypeEnum), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)