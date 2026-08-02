from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tree import Tree
from app.schemas.tree import TreeCreate

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