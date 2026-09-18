"""
Бизнес-логика для работы с персонами.
Автоматически подставляет фамилию и отчество от отца,
создает события жизни и родственные связи.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Person, LifeEvent, EventTypeEnum, Relationship, RelationshipTypeEnum
from app.services.patronymic_service import generate_patronymic


async def auto_create_life_events_and_relationships(
        db: AsyncSession,
        person: Person,
        father_id: int | None = None,
        mother_id: int | None = None
):
    """
    Комплексная бизнес-логика при создании персоны:

    1. Подставляет фамилию отца, если она не указана у ребенка.
    2. Подставляет отчество от отца с учетом культуры (ru, uk, kk, sv, is и т.д.).
    3. Создает события BIRTH и DEATH, если указаны соответствующие даты.
    4. Создает связи biological_parent с указанными родителями.

    Args:
        db: Асинхронная сессия базы данных
        person: Объект персоны (уже добавлен в сессию, но не закоммичен)
        father_id: ID биологического отца (опционально)
        mother_id: ID биологической матери (опционально)
    """

    # ==========================================
    # 1. АВТОПОДСТАНОВКА ФАМИЛИИ И ОТЧЕСТВА ОТ ОТЦА
    # ==========================================
    if father_id:
        father_res = await db.execute(select(Person).where(Person.id == father_id))
        father = father_res.scalar_one_or_none()

        if father:
            # Автоподстановка фамилии
            if not person.last_name and father.last_name:
                person.last_name = father.last_name

            # Автоподстановка отчества с учетом культуры
            if not person.middle_name and person.gender and father.first_name:
                # Используем культуру ребенка, если указана, иначе культуру отца, иначе русскую по умолчанию
                culture = person.culture or father.culture or "ru"
                person.middle_name = generate_patronymic(
                    father.first_name,
                    person.gender,
                    culture
                )

    # ==========================================
    # 2. СОЗДАНИЕ СОБЫТИЙ ЖИЗНИ (BIRTH и DEATH)
    # ==========================================

    # Событие рождения
    if person.birth_date:
        existing_birth = await db.execute(
            select(LifeEvent).where(
                LifeEvent.person_id == person.id,
                LifeEvent.event_type == EventTypeEnum.BIRTH
            )
        )
        if not existing_birth.scalar_one_or_none():
            db.add(LifeEvent(
                person_id=person.id,
                event_type=EventTypeEnum.BIRTH,
                event_date=person.birth_date,
                location=person.birth_place,
                is_date_approx=person.is_birth_date_approx
            ))

    # Событие смерти
    if person.death_date:
        existing_death = await db.execute(
            select(LifeEvent).where(
                LifeEvent.person_id == person.id,
                LifeEvent.event_type == EventTypeEnum.DEATH
            )
        )
        if not existing_death.scalar_one_or_none():
            db.add(LifeEvent(
                person_id=person.id,
                event_type=EventTypeEnum.DEATH,
                event_date=person.death_date,
                location=person.death_place,
                is_date_approx=person.is_death_date_approx
            ))

    # ==========================================
    # 3. СОЗДАНИЕ СВЯЗЕЙ С РОДИТЕЛЯМИ
    # ==========================================

    # Связь с отцом
    if father_id:
        db.add(Relationship(
            from_person_id=father_id,
            to_person_id=person.id,
            relationship_type=RelationshipTypeEnum.BIOLOGICAL_PARENT,
            is_current=True
        ))

    # Связь с матерью
    if mother_id:
        db.add(Relationship(
            from_person_id=mother_id,
            to_person_id=person.id,
            relationship_type=RelationshipTypeEnum.BIOLOGICAL_PARENT,
            is_current=True
        ))