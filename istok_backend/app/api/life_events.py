from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.life_event import TimelineResponse, LifeEventCreate, LifeEventResponse, LifeEventUpdate
from app.services import life_event_service, access_service
from app.models.user import User

router = APIRouter(prefix="/persons/{person_id}", tags=["Life Events"])


@router.get("/timeline/", response_model=TimelineResponse)
async def get_person_timeline(
        person_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Возвращает хронологический таймлайн жизни персоны."""
    # Проверяем права доступа к персоне
    has_access = await access_service.check_person_access(db, person_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой персоне"
        )

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
    """Добавляет новое событие жизни к персоне (вручную)."""
    # Проверяем права доступа к персоне
    has_access = await access_service.check_person_access(db, person_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой персоне"
        )

    try:
        new_event = await life_event_service.create_life_event(db, person_id, event_in)
        return new_event
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/events/{event_id}", response_model=LifeEventResponse)
async def update_life_event_endpoint(
        person_id: UUID,
        event_id: UUID,
        event_in: LifeEventUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Обновляет вручную созданное событие жизни."""
    # Проверяем права доступа к персоне
    has_access = await access_service.check_person_access(db, person_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой персоне"
        )

    try:
        updated_event = await life_event_service.update_life_event(db, person_id, event_id, event_in)
        return updated_event
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_life_event_endpoint(
        person_id: UUID,
        event_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Удаляет вручную созданное событие жизни."""
    # Проверяем права доступа к персоне
    has_access = await access_service.check_person_access(db, person_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой персоне"
        )

    try:
        await life_event_service.delete_life_event(db, person_id, event_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))