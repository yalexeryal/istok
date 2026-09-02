from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tree import Tree
from app.schemas.tree import TreeCreate, TreeUpdate
from sqlalchemy import delete
from app.models.tree_person import TreePerson
from app.models.relation import Relation
from app.models.life_event import LifeEvent
from app.models.person import Person
from app.models.access_request import AccessRequest
from app.services.access_service import check_tree_access
from uuid import UUID

async def create_tree(db: AsyncSession, owner_id: UUID, tree_in: TreeCreate) -> Tree:
    """Создает новое дерево для пользователя"""
    new_tree = Tree(
        name=tree_in.name,
        owner_id=owner_id,
        is_public=tree_in.is_public
    )
    db.add(new_tree)
    await db.commit()
    await db.refresh(new_tree)
    return new_tree

async def get_user_trees(db: AsyncSession, owner_id: UUID) -> list[Tree]:
    """Получает все деревья пользователя"""
    result = await db.execute(
        select(Tree).where(Tree.owner_id == owner_id).order_by(Tree.created_at.desc())
    )
    return result.scalars().all()


async def update_tree(
        db: AsyncSession,
        tree_id: UUID,
        user_id: UUID,
        tree_in: "TreeUpdate"
) -> "Tree":
    """Обновляет дерево (только для владельца)."""


    # Проверка: только владелец может редактировать дерево
    result = await db.execute(select(Tree).where(Tree.id == tree_id, Tree.owner_id == user_id))
    tree = result.scalar_one_or_none()
    if not tree:
        raise ValueError("Дерево не найдено или у вас нет прав на его редактирование")

    update_data = tree_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tree, field, value)

    await db.commit()
    await db.refresh(tree)
    return tree


async def delete_tree(db: AsyncSession, tree_id: UUID, user_id: UUID) -> None:
    """Удаляет дерево и все связанные данные."""
    # Проверка: только владелец может удалять дерево
    result = await db.execute(select(Tree).where(Tree.id == tree_id, Tree.owner_id == user_id))
    tree = result.scalar_one_or_none()
    if not tree:
        raise ValueError("Дерево не найдено или у вас нет прав на его удаление")

    # Получаем все персоны дерева
    tp_result = await db.execute(
        select(TreePerson.person_id).where(TreePerson.tree_id == tree_id)
    )
    person_ids = [row[0] for row in tp_result.all()]

    if person_ids:
        # Удаляем связи между этими персонами
        await db.execute(delete(Relation).where(
            (Relation.person_1_id.in_(person_ids)) | (Relation.person_2_id.in_(person_ids))
        ))
        # Удаляем события этих персон
        await db.execute(delete(LifeEvent).where(LifeEvent.person_id.in_(person_ids)))
        # Удаляем сами персоны
        await db.execute(delete(Person).where(Person.id.in_(person_ids)))

    # Удаляем запросы на доступ к этому дереву
    await db.execute(delete(AccessRequest).where(AccessRequest.tree_id == tree_id))

    # Удаляем привязки tree_persons
    await db.execute(delete(TreePerson).where(TreePerson.tree_id == tree_id))

    # Удаляем само дерево
    await db.execute(delete(Tree).where(Tree.id == tree_id))

    await db.commit()