from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.tree_person import TreePerson
from app.models.person import Person
from app.models.relation import Relation


async def get_tree_graph(db: AsyncSession, tree_id: UUID) -> dict:
    """
    Собирает граф дерева: всех людей и связи только между ними.
    """
    # 1. Получаем все person_id, принадлежащие этому дереву
    tp_result = await db.execute(
        select(TreePerson.person_id).where(TreePerson.tree_id == tree_id)
    )
    person_ids = [row[0] for row in tp_result.all()]

    if not person_ids:
        return {"nodes": [], "edges": []}

    # 2. Получаем данные всех этих персон
    persons_result = await db.execute(
        select(Person).where(Person.id.in_(person_ids))
    )
    persons = persons_result.scalars().all()

    nodes = []
    for p in persons:
        nodes.append({
            "id": str(p.id),
            "first_name": p.first_name,
            "last_name": p.last_name,
            "middle_name": p.middle_name,
            "birth_date": str(p.birth_date) if p.birth_date else None,
            "death_date": str(p.death_date) if p.death_date else None,
            "gender": p.gender.value if p.gender else None,
            "photo_url": p.photo_url
        })

    # 3. Получаем все связи, где ОБА человека находятся в этом дереве
    relations_result = await db.execute(
        select(Relation).where(
            Relation.person_1_id.in_(person_ids),
            Relation.person_2_id.in_(person_ids)
        )
    )
    relations = relations_result.scalars().all()

    edges = []
    for r in relations:
        edges.append({
            "id": str(r.id),
            "source": str(r.person_1_id),
            "target": str(r.person_2_id),
            "type": r.type.value
        })

    return {"nodes": nodes, "edges": edges}