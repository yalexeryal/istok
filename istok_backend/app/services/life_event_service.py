from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.life_event import LifeEvent, EventTypeEnum, EventSourceEnum
from app.models.person import Person
from app.schemas.life_event import TimelineResponse, LifeEventResponse, LifeEventCreate


async def get_person_timeline(db: AsyncSession, person_id: UUID) -> TimelineResponse | None:
    """Получает таймлайн жизни персоны."""
    person_result = await db.execute(select(Person).where(Person.id == person_id))
    person = person_result.scalar_one_or_none()

    if not person:
        return None

    events_result = await db.execute(
        select(LifeEvent)
        .where(LifeEvent.person_id == person_id)
        .order_by(LifeEvent.date.asc().nulls_last(), LifeEvent.created_at.desc())
    )
    events = events_result.scalars().all()

    event_responses = [
        LifeEventResponse(
            id=e.id,
            event_type=e.event_type.value,
            date=e.date,
            date_approx=e.date_approx,
            place=e.place,
            description=e.description,
            source=e.source.value,
            created_at=e.created_at
        ) for e in events
    ]

    full_name = f"{person.last_name} {person.first_name} {person.middle_name or ''}".strip()

    return TimelineResponse(
        person_id=person.id,
        full_name=full_name,
        events=event_responses
    )


async def create_life_event(
        db: AsyncSession,
        person_id: UUID,
        event_in: LifeEventCreate
) -> LifeEvent:
    """
    Создает новое событие жизни для персоны (вручную добавленное пользователем).
    """
    # 1. Проверяем, что персона существует
    person_result = await db.execute(select(Person).where(Person.id == person_id))
    person = person_result.scalar_one_or_none()

    if not person:
        raise ValueError("Персона не найдена")

    # 2. Валидируем тип события (только ручные типы разрешены для добавления)
    allowed_manual_types = [
        EventTypeEnum.EDUCATION,
        EventTypeEnum.MILITARY_SERVICE,
        EventTypeEnum.WORK,
        EventTypeEnum.RELOCATION,
        EventTypeEnum.AWARD,
        EventTypeEnum.OTHER
    ]

    try:
        event_type = EventTypeEnum(event_in.event_type.lower())
    except ValueError:
        raise ValueError(f"Неизвестный тип события: {event_in.event_type}")

    if event_type not in allowed_manual_types:
        raise ValueError(
            f"Тип '{event_in.event_type}' создается автоматически. "
            f"Разрешенные типы: education, military_service, work, relocation, award, other"
        )

    # 3. Создаем событие
    new_event = LifeEvent(
        person_id=person_id,
        event_type=event_type,
        date=event_in.date,
        date_approx=event_in.date_approx,
        place=event_in.place,
        description=event_in.description,
        source=EventSourceEnum.MANUAL  # Всегда MANUAL для ручного добавления
    )

    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)

    return new_event