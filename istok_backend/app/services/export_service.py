from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.tree import Tree
from app.models.person import Person
from app.models.tree_person import TreePerson
from app.models.relation import Relation, RelationTypeEnum
from app.models.life_event import LifeEvent
from app.services.access_service import check_tree_access
from datetime import datetime


async def export_tree_to_json(db: AsyncSession, tree_id: UUID, user_id: UUID) -> dict:
    """Экспортирует полное дерево в структурированный JSON."""
    # 1. Проверка прав
    if not await check_tree_access(db, tree_id, user_id):
        raise ValueError("У вас нет доступа к этому дереву")

    # 2. Получаем дерево
    tree_res = await db.execute(select(Tree).where(Tree.id == tree_id))
    tree = tree_res.scalar_one_or_none()

    # 3. Получаем всех персон дерева
    tp_res = await db.execute(
        select(Person).join(TreePerson, Person.id == TreePerson.person_id)
        .where(TreePerson.tree_id == tree_id)
    )
    persons = tp_res.scalars().all()
    person_ids = [p.id for p in persons]

    # 4. Получаем все события этих персон
    events_res = await db.execute(
        select(LifeEvent).where(LifeEvent.person_id.in_(person_ids))
        .order_by(LifeEvent.date.asc())
    )
    events = events_res.scalars().all()

    # 5. Получаем все связи между этими персонами
    relations_res = await db.execute(
        select(Relation).where(
            Relation.person_1_id.in_(person_ids),
            Relation.person_2_id.in_(person_ids)
        )
    )
    relations = relations_res.scalars().all()

    # 6. Формируем ответ
    return {
        "tree": {
            "id": str(tree.id),
            "name": tree.name,
            "is_public": tree.is_public,
            "created_at": tree.created_at.isoformat() if tree.created_at else None
        },
        "persons": [
            {
                "id": str(p.id),
                "first_name": p.first_name,
                "last_name": p.last_name,
                "middle_name": p.middle_name,
                "birth_date": p.birth_date.isoformat() if p.birth_date else None,
                "death_date": p.death_date.isoformat() if p.death_date else None,
                "gender": p.gender.value if p.gender else None,
                "photo_url": p.photo_url
            } for p in persons
        ],
        "life_events": [
            {
                "id": str(e.id),
                "person_id": str(e.person_id),
                "event_type": e.event_type.value,
                "date": e.date.isoformat() if e.date else None,
                "description": e.description,
                "source": e.source.value
            } for e in events
        ],
        "relations": [
            {
                "id": str(r.id),
                "person_1_id": str(r.person_1_id),
                "person_2_id": str(r.person_2_id),
                "type": r.type.value
            } for r in relations
        ],
        "exported_at": datetime.utcnow().isoformat()
    }


async def export_tree_to_gedcom(db: AsyncSession, tree_id: UUID, user_id: UUID) -> str:
    """Экспортирует дерево в стандартный формат GEDCOM 5.5.1"""
    if not await check_tree_access(db, tree_id, user_id):
        raise ValueError("У вас нет доступа к этому дереву")

    tree_res = await db.execute(select(Tree).where(Tree.id == tree_id))
    tree = tree_res.scalar_one_or_none()

    tp_res = await db.execute(
        select(Person).join(TreePerson, Person.id == TreePerson.person_id)
        .where(TreePerson.tree_id == tree_id)
    )
    persons = tp_res.scalars().all()
    person_ids = [p.id for p in persons]

    events_res = await db.execute(
        select(LifeEvent).where(LifeEvent.person_id.in_(person_ids))
    )
    events_by_person = {}
    for e in events_res.scalars().all():
        if e.person_id not in events_by_person:
            events_by_person[e.person_id] = []
        events_by_person[e.person_id].append(e)

    relations_res = await db.execute(
        select(Relation).where(
            Relation.person_1_id.in_(person_ids),
            Relation.person_2_id.in_(person_ids)
        )
    )
    relations = relations_res.scalars().all()

    lines = []
    lines.append("0 HEAD")
    lines.append("1 SOUR ISTOK")
    lines.append("2 NAME Исток")
    lines.append("1 GEDC")
    lines.append("2 VERS 5.5.1")
    lines.append("2 FORM LINEAGE-LINKED")
    lines.append("1 CHAR UTF-8")
    lines.append(f"0 SUBM @SUBM1@")
    lines.append("1 NAME Владелец дерева")

    # Индивиды (INDI)
    for p in persons:
        lines.append(f"0 @{p.id}@ INDI")
        lines.append(f"1 NAME {p.first_name or 'Unknown'} /{p.last_name or 'Unknown'}/")
        if p.gender:
            sex = "M" if p.gender.value == "male" else "F" if p.gender.value == "female" else "U"
            lines.append(f"1 SEX {sex}")

        if p.birth_date:
            lines.append("1 BIRT")
            lines.append(f"2 DATE {p.birth_date.strftime('%d %b %Y').upper()}")

        if p.death_date:
            lines.append("1 DEAT")
            lines.append(f"2 DATE {p.death_date.strftime('%d %b %Y').upper()}")

        # События
        if p.id in events_by_person:
            for ev in events_by_person[p.id]:
                if ev.event_type.value == "marriage":
                    lines.append("1 MARR")
                    if ev.date:
                        lines.append(f"2 DATE {ev.date.strftime('%d %b %Y').upper()}")
                elif ev.event_type.value == "education":
                    lines.append("1 EDUC")
                    if ev.description:
                        lines.append(f"2 NOTE {ev.description}")

    # Семьи (FAM) - упрощенно на основе связей spouse
    fam_id_counter = 1
    for r in relations:
        if r.type.value == "spouse":
            lines.append(f"0 @FAM{fam_id_counter}@ FAM")
            lines.append(f"1 HUSB @{r.person_1_id}@")
            lines.append(f"1 WIFE @{r.person_2_id}@")
            fam_id_counter += 1

    lines.append("0 TRLR")

    return "\n".join(lines)