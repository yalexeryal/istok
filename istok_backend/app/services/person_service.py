from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Person, LifeEvent, EventTypeEnum


async def auto_create_life_events(db: AsyncSession, person: Person):
    """Автоматически создает события BIRTH и DEATH, если указаны даты."""
    if person.birth_date:
        existing = await db.execute(
            select(LifeEvent).where(LifeEvent.person_id == person.id, LifeEvent.event_type == EventTypeEnum.BIRTH)
        )
        if not existing.scalar_one_or_none():
            db.add(LifeEvent(
                person_id=person.id,
                event_type=EventTypeEnum.BIRTH,
                event_date=person.birth_date,
                location=person.birth_place,
                is_date_approx=person.is_birth_date_approx
            ))

    if person.death_date:
        existing = await db.execute(
            select(LifeEvent).where(LifeEvent.person_id == person.id, LifeEvent.event_type == EventTypeEnum.DEATH)
        )
        if not existing.scalar_one_or_none():
            db.add(LifeEvent(
                person_id=person.id,
                event_type=EventTypeEnum.DEATH,
                event_date=person.death_date,
                location=person.death_place,
                is_date_approx=person.is_death_date_approx
            ))