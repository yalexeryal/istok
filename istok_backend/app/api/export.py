from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services import export_service
from app.models.user import User
import json

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/trees/{tree_id}/json")
async def export_tree_json(
        tree_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Экспорт дерева в формате JSON."""
    try:
        data = await export_service.export_tree_to_json(db, tree_id, current_user.id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/trees/{tree_id}/gedcom")
async def export_tree_gedcom(
        tree_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Экспорт дерева в стандартном генеалогическом формате GEDCOM (.ged)"""
    try:
        gedcom_text = await export_service.export_tree_to_gedcom(db, tree_id, current_user.id)

        # Возвращаем файл для скачивания
        return Response(
            content=gedcom_text,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=tree_{tree_id}.ged"}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))