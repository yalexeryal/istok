from pydantic import BaseModel, Field
from datetime import date
from uuid import UUID
from typing import Optional, List

class PersonCreate(BaseModel):
    first_name: str = Field(..., max_length=100, description="Имя")
    last_name: str = Field(..., max_length=100, description="Фамилия")
    middle_name: Optional[str] = Field(None, max_length=100, description="Отчество")
    birth_date: Optional[date] = Field(None, description="Дата рождения")
    birth_place: Optional[str] = Field(None, max_length=200, description="Место рождения")
    death_date: Optional[date] = Field(None, description="Дата смерти")
    death_place: Optional[str] = Field(None, max_length=200, description="Место смерти")
    gender: Optional[str] = Field(None, description="male или female")
    photo_url: Optional[str] = Field(None, description="Ссылка на фото")

class PersonMatch(BaseModel):
    person_id: UUID
    full_name: str
    owner_name: str  # Имя владельца дерева (для приватности название дерева не раскрываем)

class PersonAddResponse(BaseModel):
    status: str  # "created" или "match_found_and_requested"
    person_id: Optional[UUID] = None
    message: str
    matches: Optional[List[PersonMatch]] = None

class PersonSearchResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    similarity: float = Field(..., description="Процент совпадения (0.0 - 1.0)")

    class Config:
        from_attributes = True