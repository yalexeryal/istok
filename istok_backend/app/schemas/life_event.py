from pydantic import BaseModel, Field
from datetime import date as DateType, datetime
from uuid import UUID
from typing import Optional, List

class LifeEventCreate(BaseModel):
    event_type: str = Field(..., description="Тип события: education, military_service, work, relocation, award, other")
    date: Optional[DateType] = Field(None, description="Дата события")
    date_approx: bool = Field(False, description="Если дата приблизительная")
    place: Optional[str] = Field(None, max_length=200, description="Место события")
    description: Optional[str] = Field(None, description="Детали")

class LifeEventUpdate(BaseModel):
    event_type: Optional[str] = Field(None, description="Тип события")
    date: Optional[DateType] = Field(None, description="Дата события")
    date_approx: Optional[bool] = Field(None, description="Если дата приблизительная")
    place: Optional[str] = Field(None, max_length=200, description="Место события")
    description: Optional[str] = Field(None, description="Детали")

class LifeEventResponse(BaseModel):
    id: UUID
    event_type: str
    date: Optional[DateType] = None
    date_approx: bool = False
    place: Optional[str] = None
    description: Optional[str] = None
    source: str
    created_at: datetime

    class Config:
        from_attributes = True

class TimelineResponse(BaseModel):
    person_id: UUID
    full_name: str
    events: List[LifeEventResponse]