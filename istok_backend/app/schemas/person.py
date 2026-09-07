from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from uuid import UUID


class PersonBase(BaseModel):
    first_name: str = Field(..., max_length=100, description="Имя")
    last_name: str = Field(..., max_length=100, description="Фамилия (актуальная)")
    maiden_name: Optional[str] = Field(None, max_length=100, description="Девичья фамилия (для женщин)")
    middle_name: Optional[str] = Field(None, max_length=100, description="Отчество")
    birth_date: Optional[date] = None
    birth_place: Optional[str] = Field(None, max_length=200)
    death_date: Optional[date] = None
    death_place: Optional[str] = Field(None, max_length=200)
    burial_place: Optional[str] = Field(None, max_length=200)
    gender: Optional[str] = None
    photo_url: Optional[str] = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    maiden_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    birth_place: Optional[str] = None
    death_date: Optional[date] = None
    death_place: Optional[str] = None
    burial_place: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None


class PersonResponse(PersonBase):
    id: UUID
    created_at: Optional[str] = None

    class Config:
        from_attributes = True