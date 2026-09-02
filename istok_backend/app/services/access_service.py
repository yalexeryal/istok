from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.tree import Tree
from app.models.tree_person import TreePerson
from app.models.access_request import AccessRequest, RequestStatusEnum  # <-- ДОБАВИТЬ ЭТОТ ИМПОРТ


async def check_tree_access(
        db: AsyncSession,
        tree_id: UUID,
        user_id: UUID
) -> bool:
    # 1. Владелец
    tree_result = await db.execute(select(Tree).where(Tree.id == tree_id, Tree.owner_id == user_id))
    if tree_result.scalar_one_or_none():
        return True

    # 2. Добавлял персоны
    tp_result = await db.execute(
        select(TreePerson).where(TreePerson.tree_id == tree_id, TreePerson.added_by == user_id)
    )
    if tp_result.scalar_one_or_none():
        return True

    # 3. Одобренный запрос на коллаборацию <-- НОВОЕ
    req_result = await db.execute(
        select(AccessRequest).where(
            AccessRequest.tree_id == tree_id,
            AccessRequest.requester_id == user_id,
            AccessRequest.status == RequestStatusEnum.APPROVED
        )
    )
    if req_result.scalar_one_or_none():
        return True

    return False