from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, Any

class NotificationResponse(BaseModel):
    id: UUID
    type: str  # Тип уведомления (new_request, request_approved, person_found)
    message: str  # Человекочитаемое сообщение
    payload: Optional[dict[str, Any]] = None  # Сырые данные для дополнительных действий
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class MarkAsReadResponse(BaseModel):
    """Ответ после отметки уведомлений как прочитанных"""
    marked_count: int
    message: str