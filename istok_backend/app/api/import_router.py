from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.gedcom_service import import_gedcom_to_tree

router = APIRouter(prefix="/import", tags=["Import"])


@router.post("/gedcom/{tree_id}", response_model=dict)
async def import_gedcom(
        tree_id: str,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Импортирует дерево из GEDCOM файла."""

    # 1. Проверка расширения файла
    if not file.filename.lower().endswith('.ged'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл должен иметь расширение .ged")

    # 2. Временное сохранение файла
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.ged")

    try:
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 3. Запуск импорта
        stats = await import_gedcom_to_tree(db, tree_id, current_user.id, temp_file_path)

        return {
            "message": "GEDCOM успешно импортирован",
            "stats": stats
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ошибка импорта: {str(e)}")
    finally:
        # 4. Очистка временного файла
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)