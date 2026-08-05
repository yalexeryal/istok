from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.tree import Tree
from app.models.tree_person import TreePerson


async def check_tree_access(
        db: AsyncSession,
        tree_id: UUID,
        user_id: UUID
) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к дереву.
    Доступ есть, если пользователь является владельцем дерева
    ИЛИ добавлял хотя бы одну персону в это дерево.
    """
    # 1. Проверяем, является ли пользователь владельцем
    tree_result = await db.execute(
        select(Tree).where(Tree.id == tree_id, Tree.owner_id == user_id)
    )
    if tree_result.scalar_one_or_none():
        return True

    # 2. Проверяем, добавлял ли пользователь персон в это дерево
    tp_result = await db.execute(
        select(TreePerson).where(
            TreePerson.tree_id == tree_id,
            TreePerson.added_by == user_id
        )
    )
    if tp_result.scalar_one_or_none():
        return True

    return False


async def check_person_access(
        db: AsyncSession,
        person_id: UUID,
        user_id: UUID
) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к персоне.
    Доступ есть, если персона принадлежит хотя бы одному дереву,
    к которому у пользователя есть доступ.
    """
    # Находим все деревья, в которых есть эта персона
    tree_ids_result = await db.execute(
        select(TreePerson.tree_id).where(TreePerson.person_id == person_id)
    )
    tree_ids = [row[0] for row in tree_ids_result.all()]

    if not tree_ids:
        return False

    # Проверяем доступ хотя бы к одному из этих деревьев
    for tree_id in tree_ids:
        if await check_tree_access(db, tree_id, user_id):
            return True

    return False