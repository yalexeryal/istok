from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from app.models.models import GenderEnum, EventTypeEnum

class PersonBase(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    maiden_name: Optional[str] = None
    birth_date: Optional[date] = None
    is_birth_date_approx: Optional[bool] = False
    death_date: Optional[date] = None
    is_death_date_approx: Optional[bool] = False
    birth_place: Optional[str] = None
    death_place: Optional[str] = None
    burial_place: Optional[str] = None
    gender: Optional[GenderEnum] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None
    tree_id: Optional[int] = 1

class PersonCreate(PersonBase):
    pass

class PersonResponse(PersonBase):
    id: int
    created_at: datetime
    updated_at: datetime
    updated_by_id: Optional[int] = None
    full_name_display: str
    model_config = ConfigDict(from_attributes=True)

class LifeEventBase(BaseModel):
    event_type: EventTypeEnum
    event_date: Optional[date] = None
    end_date: Optional[date] = None
    is_date_approx: Optional[bool] = False
    location: Optional[str] = None
    description: Optional[str] = None
    related_person_id: Optional[int] = None

class LifeEventCreate(LifeEventBase):
    person_id: int

class LifeEventResponse(LifeEventBase):
    id: int
    person_id: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)