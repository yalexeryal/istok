from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.relation import Relation, RelationTypeEnum
from app.models.person import Person
from app.models.life_event import LifeEvent, EventTypeEnum, EventSourceEnum
from app.schemas.relation import RelationCreate


async def create_relation(
        db: AsyncSession,
        user_id: UUID,
        relation_in: RelationCreate
) -> Relation:
    """Создает связь между людьми и автоматически генерирует события жизни."""

    # 1. Валидация: проверяем, что оба человека существуют
    result = await db.execute(select(Person).where(Person.id.in_([relation_in.person_1_id, relation_in.person_2_id])))
    persons = result.scalars().all()
    if len(persons) != 2:
        raise ValueError("Один или оба человека не найдены в базе данных")

    # 2. Валидация: проверяем, что связь такого типа еще не существует
    existing = await db.execute(
        select(Relation).where(
            Relation.person_1_id.in_([relation_in.person_1_id, relation_in.person_2_id]),
            Relation.person_2_id.in_([relation_in.person_1_id, relation_in.person_2_id]),
            Relation.type == RelationTypeEnum(relation_in.type)
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Такая связь уже существует между этими людьми")

    # 3. Создаем саму связь
    new_relation = Relation(
        person_1_id=relation_in.person_1_id,
        person_2_id=relation_in.person_2_id,
        type=RelationTypeEnum(relation_in.type),
        created_by=user_id
    )
    db.add(new_relation)
    await db.flush()

    # 4. АВТОМАТИЧЕСКОЕ СОЗДАНИЕ СОБЫТИЙ ЖИЗНИ
    person_1 = next(p for p in persons if p.id == relation_in.person_1_id)
    person_2 = next(p for p in persons if p.id == relation_in.person_2_id)

    if relation_in.type == "parent_child":
        # person_1 — родитель, person_2 — ребенок
        # Создаем событие CHILD_BIRTH для родителя
        event_date = relation_in.event_date or person_2.birth_date
        if event_date:
            child_birth_event = LifeEvent(
                person_id=person_1.id,
                event_type=EventTypeEnum.CHILD_BIRTH,
                date=event_date,
                description=f"Рождение ребенка: {person_2.first_name} {person_2.last_name}",
                source=EventSourceEnum.AUTO
            )
            db.add(child_birth_event)

    elif relation_in.type == "spouse":
        # Создаем событие MARRIAGE для обоих супругов
        for person in [person_1, person_2]:
            marriage_event = LifeEvent(
                person_id=person.id,
                event_type=EventTypeEnum.MARRIAGE,
                date=relation_in.event_date,
                description=f"Брак с {person_2.first_name if person.id == person_1.id else person_1.first_name}",
                source=EventSourceEnum.AUTO
            )
            db.add(marriage_event)