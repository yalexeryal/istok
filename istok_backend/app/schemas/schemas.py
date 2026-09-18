from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from app.models.models import GenderEnum, EventTypeEnum, RelationshipTypeEnum

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
    culture: Optional[str] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None
    tree_id: Optional[int] = 1

class PersonCreate(PersonBase):
    # Добавляем поля для удобства создания связей при регистрации персоны
    father_id: Optional[int] = None
    mother_id: Optional[int] = None

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

class RelationshipBase(BaseModel):
    from_person_id: int
    to_person_id: int
    relationship_type: RelationshipTypeEnum
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = True
    description: Optional[str] = None

class RelationshipCreate(RelationshipBase):
    pass

class RelationshipResponse(RelationshipBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)