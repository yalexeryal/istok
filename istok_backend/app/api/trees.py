"""
Роутер для управления генеалогическими деревьями и правами доступа.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import Tree, TreeCollaborator, CollaboratorRoleEnum, User
from app.schemas.schemas import TreeCreate, TreeResponse, CollaboratorCreate, CollaboratorResponse
from app.services.access_service import check_tree_access

router = APIRouter(prefix="/trees", tags=["Trees"])


@router.post("/", response_model=TreeResponse, status_code=201)
async def create_tree(tree: TreeCreate, db: AsyncSession = Depends(get_db)):
    """Создание нового дерева. Создатель автоматически становится владельцем."""
    # Создаём дерево
    db_tree = Tree(**tree.model_dump())
    db.add(db_tree)
    await db.flush()

    # Создаём запись о владельце (user_id=1 для тестов, в реальности берём из токена)
    collaborator = TreeCollaborator(
        tree_id=db_tree.id,
        user_id=1,  # TODO: Получить из JWT токена
        role=CollaboratorRoleEnum.OWNER,
        can_invite=True
    )
    db.add(collaborator)
    await db.commit()
    await db.refresh(db_tree)
    return db_tree


@router.get("/", response_model=list[TreeResponse])
async def get_trees(db: AsyncSession = Depends(get_db)):
    """Получение списка деревьев, к которым пользователь имеет доступ."""
    result = await db.execute(
        select(TreeCollaborator).where(TreeCollaborator.user_id == 1)  # TODO: Из токена
    )
    collaborators = result.scalars().all()
    tree_ids = [c.tree_id for c in collaborators]

    result = await db.execute(select(Tree).where(Tree.id.in_(tree_ids)))
    return result.scalars().all()


@router.get("/{tree_id}", response_model=TreeResponse)
async def get_tree(tree_id: int, db: AsyncSession = Depends(get_db)):
    """Получение информации о дереве."""
    result = await db.execute(select(Tree).where(Tree.id == tree_id))
    tree = result.scalar_one_or_none()
    if not tree:
        raise HTTPException(status_code=404, detail="Дерево не найдено")
    return tree


@router.post("/{tree_id}/collaborators", response_model=CollaboratorResponse, status_code=201)
async def add_collaborator(
        tree_id: int,
        collaborator: CollaboratorCreate,
        db: AsyncSession = Depends(get_db)
):
    """Добавление соавтора к дереву."""
    # Проверяем, что текущий пользователь имеет право приглашать
    await check_tree_access(db, tree_id, 1, CollaboratorRoleEnum.OWNER)  # TODO: Из токена

    # Проверяем, что пользователь существует
    result = await db.execute(select(User).where(User.id == collaborator.user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверяем, не добавлен ли уже
    result = await db.execute(
        select(TreeCollaborator).where(
            TreeCollaborator.tree_id == tree_id,
            TreeCollaborator.user_id == collaborator.user_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь уже является соавтором")

    # Создаём запись о соавторстве
    db_collaborator = TreeCollaborator(
        tree_id=tree_id,
        user_id=collaborator.user_id,
        role=collaborator.role,
        can_invite=collaborator.can_invite
    )
    db.add(db_collaborator)
    await db.commit()
    await db.refresh(db_collaborator)
    return db_collaborator


@router.get("/{tree_id}/collaborators", response_model=list[CollaboratorResponse])
async def get_collaborators(tree_id: int, db: AsyncSession = Depends(get_db)):
    """Получение списка соавторов дерева."""
    await check_tree_access(db, tree_id, 1, CollaboratorRoleEnum.VIEWER)  # TODO: Из токена

    result = await db.execute(
        select(TreeCollaborator).where(TreeCollaborator.tree_id == tree_id)
    )
    return result.scalars().all()