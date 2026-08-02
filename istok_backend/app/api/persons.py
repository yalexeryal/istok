from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.person import PersonCreate, PersonAddResponse
from app.services import person_service
from app.models.tree import Tree
from app.models.user import User

router = APIRouter(prefix="/trees/{tree_id}/persons", tags=["Persons"])

@router.post("/", response_model=PersonAddResponse, status_code=status.HTTP_200_OK)
async def add_person_to_tree(
    tree_id: UUID,
    person_in: PersonCreate,
    force_create: bool = Query(False, description="Игнорировать предупреждения о дублях"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # <-- Заменили заглушку
):
    # Проверяем, что дерево существует
    tree_result = await db.execute(select(Tree).where(Tree.id == tree_id))
    tree = tree_result.scalar_one_or_none()
    if not tree:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Дерево не найдено")

    result = await person_service.add_person_to_tree(
        db=db,
        tree_id=tree_id,
        requester_id=current_user.id,  # <-- Используем реального пользователя
        person_in=person_in,
        force_create=force_create
    )

    return result