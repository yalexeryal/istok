from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class AccessRequestCreate(BaseModel):
    tree_id: UUID
    message: Optional[str] = None

class AccessRequestResponse(BaseModel):
    id: UUID
    tree_id: UUID
    requester_id: UUID
    requester_name: Optional[str] = None
    message: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None  # <-- ИЗМЕНЕНО: добавлен Optional и default None

    class Config:
        from_attributes = True

class AccessRequestAction(BaseModel):
    action: str  # "approve" или "reject"