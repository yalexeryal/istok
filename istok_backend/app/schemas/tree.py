from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class TreeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Название дерева")
    is_public: bool = Field(False, description="Публичное или приватное")

class TreeResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    is_public: bool
    created_at: datetime

    class Config:
        from_attributes = True