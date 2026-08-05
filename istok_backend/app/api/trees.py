from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.tree import TreeCreate, TreeResponse
from app.services import tree_service
from app.models.user import User

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