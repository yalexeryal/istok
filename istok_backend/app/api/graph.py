from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.graph import TreeGraphResponse
from app.services import graph_service, access_service
from app.models.user import User
from app.models.tree import Tree

router = APIRouter(prefix="/trees/{tree_id}/graph", tags=["Graph"])


@router.get("/", response_model=TreeGraphResponse)
async def get_tree_graph_endpoint(
        tree_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Возвращает граф дерева (узлы и связи) для визуализации на фронтенде."""
    # Проверяем, что дерево существует
    tree_result = await db.execute(select(Tree).where(Tree.id == tree_id))
    tree = tree_result.scalar_one_or_none()
    if not tree:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Дерево не найдено")

    # Проверяем права доступа к дереву
    has_access = await access_service.check_tree_access(db, tree_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому дереву"
        )

    graph_data = await graph_service.get_tree_graph(db, tree_id)
    return graph_data