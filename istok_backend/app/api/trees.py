from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.tree import TreeCreate, TreeResponse
from app.services import tree_service
from app.models.user import User
from app.schemas.tree import TreeUpdate
from uuid import UUID


router = APIRouter(prefix="/trees", tags=["Trees"])

@router.post("/", response_model=TreeResponse, status_code=status.HTTP_201_CREATED)
async def create_tree(
    tree_in: TreeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создает новое родовое дерево для текущего пользователя."""
    new_tree = await tree_service.create_tree(db, current_user.id, tree_in)
    return new_tree

@router.get("/", response_model=list[TreeResponse])
async def get_my_trees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получает список всех деревьев текущего пользователя."""
    trees = await tree_service.get_user_trees(db, current_user.id)
    return trees


@router.patch("/{tree_id}", response_model=dict)
async def update_tree(
    tree_id: UUID,
    tree_in: TreeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновляет дерево (только для владельца)."""
    try:
        tree = await tree_service.update_tree(db, tree_id, current_user.id, tree_in)
        return {"message": "Дерево успешно обновлено", "tree_id": str(tree.id)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{tree_id}", response_model=dict)
async def delete_tree(
    tree_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаляет дерево и все связанные данные (персон, связи, события)."""
    try:
        await tree_service.delete_tree(db, tree_id, current_user.id)
        return {"message": "Дерево успешно удалено"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))