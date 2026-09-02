from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.access_request import AccessRequestCreate, AccessRequestResponse, AccessRequestAction
from app.services import access_request_service
from app.models.user import User
from pydantic import BaseModel
from uuid import UUID
from typing import Optional



router = APIRouter(prefix="/access-requests", tags=["Access Requests"])

class AccessRequestCreate(BaseModel):
    tree_id: UUID
    person_id: Optional[UUID] = None  # Опционально: если запрашиваем доступ к конкретной персоне

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def send_access_request(
    request_in: AccessRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отправляет запрос на доступ к дереву."""
    try:
        req = await access_request_service.create_access_request(
            db, current_user.id, request_in.tree_id, request_in.person_id
        )
        return {"message": "Запрос на доступ успешно отправлен", "request_id": str(req.id)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/tree/{tree_id}", response_model=list[AccessRequestResponse])
async def get_pending_requests(
    tree_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        requests = await access_request_service.get_tree_requests(db, tree_id, current_user.id)
        return requests
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.post("/{request_id}/respond", response_model=dict)
async def respond_to_request(
    request_id: UUID,
    action: AccessRequestAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        await access_request_service.respond_to_request(db, request_id, current_user.id, action.action)
        status_msg = "одобрен" if action.action == "approve" else "отклонен"
        return {"message": f"Запрос успешно {status_msg}"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))