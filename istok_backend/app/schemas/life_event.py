from pydantic import BaseModel, Field
from datetime import date, datetime
from uuid import UUID
from typing import Optional, List

class LifeEventCreate(BaseModel):
    event_type: str = Field(
        ...,
        description="Тип события: education, military_service, work, relocation, award, other"
    )
    date: Optional[date] = Field(None, description="Дата события")
    date_approx: bool = Field(False, description="Если дата приблизительная (например, 'ок. 1900')")
    place: Optional[str] = Field(None, max_length=200, description="Место события")
    description: Optional[str] = Field(None, description="Детали (название ВУЗа, должность, номер части)")

class LifeEventResponse(BaseModel):
    id: UUID
    event_type: str
    date: Optional[date] = None
    date_approx: bool = False
    place: Optional[str] = None
    description: Optional[str] = None
    source: str  # "auto" или "manual"
    created_at: datetime

    class Config:
        from_attributes = True

class TimelineResponse(BaseModel):
    person_id: UUID
    full_name: str
    events: List[LifeEventResponse]