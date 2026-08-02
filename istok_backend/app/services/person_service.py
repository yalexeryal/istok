from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from app.models.person import Person, GenderEnum
from app.models.tree import Tree
from app.models.tree_person import TreePerson
from app.models.access_request import AccessRequest, RequestStatusEnum
from app.models.notification import Notification, NotificationTypeEnum
from app.models.life_event import LifeEvent, EventTypeEnum, EventSourceEnum
from app.models.user import User
from app.schemas.person import PersonCreate, PersonMatch


async def find_similar_persons(db: AsyncSession, person_in: PersonCreate) -> list[Person]:
    """Ищет возможных дублей по имени, фамилии и дате рождения."""
    conditions = [
        Person.first_name.ilike(f"%{person_in.first_name}%"),
        Person.last_name.ilike(f"%{person_in.last_name}%")
    ]
    # Если указана дата рождения, добавляем её в условие для точности
    if person_in.birth_date:
        conditions.append(Person.birth_date == person_in.birth_date)

    stmt = select(Person).where(and_(*conditions))
    result = await db.execute(stmt)
    return result.scalars().all()


async def add_person_to_tree(
        db: AsyncSession,
        tree_id: UUID,
        requester_id: UUID,
        person_in: PersonCreate,
        force_create: bool = False
) -> dict:
    """
    Добавляет персону в дерево. Если находит дубли, отправляет запросы владельцам.
    """
    # 1. Ищем дубли
    matches = await find_similar_persons(db, person_in)

    if matches and not force_create:
        match_results = []
        requests_created = 0

        for person in matches:
            # Находим деревья, где уже есть этот человек
            tree_stmt = select(Tree).join(TreePerson, Tree.id == TreePerson.tree_id).where(
                TreePerson.person_id == person.id)
            tree_result = await db.execute(tree_stmt)
            trees = tree_result.scalars().all()

            for tree in trees:
                # Получаем имя владельца для отображения (без раскрытия названия дерева)
                owner_stmt = select(User.full_name).where(User.id == tree.owner_id)
                owner_result = await db.execute(owner_stmt)
                owner_name = owner_result.scalar_one_or_none() or "Неизвестный владелец"

                match_results.append(PersonMatch(
                    person_id=person.id,
                    full_name=f"{person.last_name} {person.first_name} {person.middle_name or ''}".strip(),
                    owner_name=owner_name
                ))

                # Проверяем, нет ли уже активного запроса от этого пользователя к этому дереву по этой персоне
                existing_req = await db.execute(
                    select(AccessRequest).where(
                        AccessRequest.requester_id == requester_id,
                        AccessRequest.tree_id == tree.id,
                        AccessRequest.person_id == person.id,
                        AccessRequest.status == RequestStatusEnum.PENDING
                    )
                )

                if not existing_req.scalar_one_or_none():
                    # Создаем запрос на доступ/объединение
                    new_request = AccessRequest(
                        requester_id=requester_id,
                        tree_id=tree.id,
                        person_id=person.id,
                        status=RequestStatusEnum.PENDING
                    )
                    db.add(new_request)

                    # Создаем уведомление для владельца дерева
                    notification = Notification(
                        user_id=tree.owner_id,
                        type=NotificationTypeEnum.NEW_REQUEST,
                        payload={
                            "requester_id": str(requester_id),
                            "person_id": str(person.id),
                            "person_name": f"{person.first_name} {person.last_name}"
                        }
                    )
                    db.add(notification)
                    requests_created += 1

        if requests_created > 0:
            await db.commit()

        return {
            "status": "match_found_and_requested",
            "message": f"Найдено {len(matches)} возможных совпадений. Запросы на подтверждение отправлены владельцам.",
            "matches": match_results,
            "person_id": None
        }

    # 2. Если совпадений нет или force_create=True, создаем новую глобальную персону
    gender_enum = None
    if person_in.gender:
        try:
            gender_enum = GenderEnum(person_in.gender.lower())
        except ValueError:
            pass

    new_person = Person(
        first_name=person_in.first_name,
        last_name=person_in.last_name,
        middle_name=person_in.middle_name,
        birth_date=person_in.birth_date,
        birth_place=person_in.birth_place,
        death_date=person_in.death_date,
        death_place=person_in.death_place,
        gender=gender_enum,
        photo_url=person_in.photo_url,
        created_by=requester_id
    )
    db.add(new_person)
    await db.flush()  # Получаем new_person.id до коммита

    # Связываем персону с деревом
    tree_person = TreePerson(
        tree_id=tree_id,
        person_id=new_person.id,
        added_by=requester_id
    )
    db.add(tree_person)

    # 3. АВТОМАТИЧЕСКОЕ СОЗДАНИЕ СОБЫТИЙ ЖИЗНИ
    if new_person.birth_date:
        birth_event = LifeEvent(
            person_id=new_person.id,
            event_type=EventTypeEnum.BIRTH,
            date=new_person.birth_date,
            place=new_person.birth_place,
            source=EventSourceEnum.AUTO
        )
        db.add(birth_event)

    if new_person.death_date:
        death_event = LifeEvent(
            person_id=new_person.id,
            event_type=EventTypeEnum.DEATH,
            date=new_person.death_date,
            place=new_person.death_place,
            source=EventSourceEnum.AUTO
        )
        db.add(death_event)

    await db.commit()
    await db.refresh(new_person)

    return {
        "status": "created",
        "message": "Персона успешно добавлена в дерево.",
        "person_id": new_person.id,
        "matches": []
    }