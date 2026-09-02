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

    # 1. Проверяем, что оба человека существуют
    result = await db.execute(
        select(Person).where(Person.id.in_([relation_in.person_1_id, relation_in.person_2_id]))
    )
    persons = result.scalars().all()
    if len(persons) != 2:
        raise ValueError("Один или оба человека не найдены в базе данных")

    person_1 = next(p for p in persons if p.id == relation_in.person_1_id)
    person_2 = next(p for p in persons if p.id == relation_in.person_2_id)

    # 2. Проверяем, что связь такого типа еще не существует
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

    # 4. АВТОМАТИЧЕСКОЕ СОЗДАНИЕ СОБЫТИЙ ЖИЗНИ
    if relation_in.type == "parent_child":
        event_date = relation_in.event_date or person_2.birth_date
        if event_date:
            db.add(LifeEvent(
                person_id=person_1.id,
                event_type=EventTypeEnum.CHILD_BIRTH,
                date=event_date,
                description=f"Рождение ребенка: {person_2.first_name} {person_2.last_name}",
                source=EventSourceEnum.AUTO
            ))
    elif relation_in.type == "spouse":
        for person in [person_1, person_2]:
            db.add(LifeEvent(
                person_id=person.id,
                event_type=EventTypeEnum.MARRIAGE,
                date=relation_in.event_date,
                description=f"Брак с {person_2.first_name if person.id == person_1.id else person_1.first_name}",
                source=EventSourceEnum.AUTO
            ))

    # 5. Сохраняем всё в базу
    await db.commit()
    await db.refresh(new_relation)
    return new_relation


async def get_person_relations(db: AsyncSession, person_id: UUID) -> list[Relation]:
    """Получает все связи конкретного человека."""
    result = await db.execute(
        select(Relation).where(
            (Relation.person_1_id == person_id) | (Relation.person_2_id == person_id)
        )
    )
    return result.scalars().all()