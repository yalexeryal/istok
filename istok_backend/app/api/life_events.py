from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.life_event import TimelineResponse, LifeEventCreate, LifeEventResponse
from app.services import life_event_service
from app.models.user import User

router = APIRouter(prefix="/persons/{person_id}", tags=["Life Events"])

@router.get("/timeline/", response_model=TimelineResponse)
async def get_person_timeline(
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Возвращает хронологический таймлайн жизни персоны.
    """
    timeline = await life_event_service.get_person_timeline(db, person_id)
    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Персона не найдена")
    return timeline

@router.post("/events/", response_model=LifeEventResponse, status_code=status.HTTP_201_CREATED)
async def add_life_event(
    person_id: UUID,
    event_in: LifeEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Добавляет новое событие жизни к персоне (вручную).
    Разрешенные типы: education, military_service, work, relocation, award, other.
    """
    try:
        new_event = await life_event_service.create_life_event(
            db=db,
            person_id=person_id,
            event_in=event_in
        )
        return new_event
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )