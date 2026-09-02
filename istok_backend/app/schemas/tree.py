from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class TreeCreate(BaseModel):
    name: str
    is_public: bool = False

class TreeResponse(BaseModel):
    id: UUID
    name: str
    is_public: bool
    owner_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class TreeUpdate(BaseModel):
    name: Optional[str] = None
    is_public: Optional[bool] = None