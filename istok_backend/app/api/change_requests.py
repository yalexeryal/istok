"""
Роутер для управления запросами на изменения персон.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.models import ChangeRequest, ChangeRequestStatusEnum, Person
from app.schemas.schemas import ChangeRequestCreate, ChangeRequestResponse
from app.services.access_service import check_person_edit_access

router = APIRouter(prefix="/change-requests", tags=["ChangeRequests"])


def get_utc_now_naive() -> datetime:
    """Возвращает текущее время UTC в формате naive datetime для совместимости с БД."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/", response_model=ChangeRequestResponse, status_code=201)
async def create_change_request(
        request: ChangeRequestCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Создание запроса на изменение персоны.
    Если пользователь имеет права редактора, изменение применяется сразу.
    Иначе создаётся запрос на рассмотрение.
    """
    user_id = request.requested_by_id or 1

    can_edit = await check_person_edit_access(db, request.person_id, user_id)

    if can_edit:
        result = await db.execute(select(Person).where(Person.id == request.person_id))
        person = result.scalar_one_or_none()

        if not person:
            raise HTTPException(status_code=404, detail="Персона не найдена")

        if request.proposed_data:
            for key, value in request.proposed_data.items():
                if hasattr(person, key):
                    setattr(person, key, value)
            person.updated_by_id = user_id

        await db.commit()
        await db.refresh(person)

        db_request = ChangeRequest(
            person_id=request.person_id,
            requested_by_id=user_id,
            owner_id=user_id,
            change_type=request.change_type,
            proposed_data=request.proposed_data,
            status=ChangeRequestStatusEnum.APPROVED,
            responded_at=get_utc_now_naive()
        )
        db.add(db_request)
        await db.commit()
        await db.refresh(db_request)
        return db_request
    else:
        result = await db.execute(select(Person).where(Person.id == request.person_id))
        person = result.scalar_one_or_none()

        if not person:
            raise HTTPException(status_code=404, detail="Персона не найдена")

        owner_id = 1  # Заглушка

        db_request = ChangeRequest(
            person_id=request.person_id,
            requested_by_id=user_id,
            owner_id=owner_id,
            change_type=request.change_type,
            proposed_data=request.proposed_data,
            status=ChangeRequestStatusEnum.PENDING
        )
        db.add(db_request)
        await db.commit()
        await db.refresh(db_request)
        return db_request


@router.get("/", response_model=list[ChangeRequestResponse])
async def get_change_requests(db: AsyncSession = Depends(get_db)):
    """Получение списка запросов на изменения для текущего пользователя."""
    user_id = 1  # TODO: Из токена

    result = await db.execute(
        select(ChangeRequest).where(
            (ChangeRequest.requested_by_id == user_id) |
            (ChangeRequest.owner_id == user_id)
        ).order_by(ChangeRequest.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{request_id}/respond", response_model=ChangeRequestResponse)
async def respond_to_change_request(
        request_id: int,
        status: str,
        comment: str = None,
        db: AsyncSession = Depends(get_db)
):
    """
    Ответ на запрос на изменение (approve/reject).
    """
    user_id = 1  # TODO: Из токена

    result = await db.execute(select(ChangeRequest).where(ChangeRequest.id == request_id))
    change_request = result.scalar_one_or_none()

    if not change_request:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    if change_request.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Только владелец может отвечать на запрос")

    if change_request.status != ChangeRequestStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Запрос уже обработан")

    if status == "approve":
        change_request.status = ChangeRequestStatusEnum.APPROVED

        if change_request.proposed_data:
            result = await db.execute(select(Person).where(Person.id == change_request.person_id))
            person = result.scalar_one_or_none()

            if person:
                for key, value in change_request.proposed_data.items():
                    if hasattr(person, key):
                        setattr(person, key, value)
    elif status == "reject":
        change_request.status = ChangeRequestStatusEnum.REJECTED
    else:
        raise HTTPException(status_code=400, detail="Неверный статус. Используйте 'approve' или 'reject'")

    change_request.responded_at = get_utc_now_naive()
    change_request.response_comment = comment

    await db.commit()
    await db.refresh(change_request)
    return change_request