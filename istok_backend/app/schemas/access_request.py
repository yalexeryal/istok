from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class AccessRequestResponse(BaseModel):
    id: UUID
    requester_id: UUID
    requester_name: str
    tree_id: UUID
    tree_name: str
    person_id: Optional[UUID] = None
    person_name: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class AccessRequestAction(BaseModel):
    """Схема для действия над запросом"""
    action: str  # "approve" или "reject"