from pydantic import BaseModel, Field
from datetime import date
from uuid import UUID
from typing import Optional

class RelationCreate(BaseModel):
    person_1_id: UUID
    person_2_id: UUID
    # Типы: parent_child, spouse, sibling
    # Для parent_child: person_1 — РОДИТЕЛЬ, person_2 — РЕБЕНОК
    type: str = Field(..., description="Тип связи: parent_child, spouse, sibling")
    event_date: Optional[date] = Field(None, description="Дата события (например, дата брака или рождения ребенка). Если не указана, возьмется из карточки ребенка.")

class RelationResponse(BaseModel):
    id: UUID
    person_1_id: UUID
    person_2_id: UUID
    type: str
    created_by: UUID

    class Config:
        from_attributes = True