from sqlalchemy import Column, Text, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class TreePerson(Base):
    __tablename__ = "tree_persons"

    tree_id = Column(UUID(as_uuid=True), ForeignKey("trees.id"), primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id"), primary_key=True)
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    private_notes = Column(Text, nullable=True)
    relation_to_owner = Column(Text, nullable=True)