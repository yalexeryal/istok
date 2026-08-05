from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.person import PersonCreate, PersonAddResponse, PersonSearchResponse
from app.services import person_service, access_service, photo_service
from app.models.tree import Tree
from app.models.person import Person
from app.models.user import User
from typing import List

router = APIRouter(tags=["Persons"])


@router.get("/persons/search", response_model=List[PersonSearchResponse])
async def search_persons(
        q: str = Query(..., min_length=1, description="Поисковый запрос"),
        limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Нечеткий поиск персон по базе данных."""
    results = await person_service.search_persons(db, q, limit)
    return results


@router.post("/trees/{tree_id}/persons/", response_model=PersonAddResponse, status_code=status.HTTP_200_OK)
async def add_person_to_tree(
        tree_id: UUID,
        person_in: PersonCreate,
        force_create: bool = Query(False, description="Игнорировать предупреждения о дублях"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Добавляет персону в дерево с проверкой дублей."""
    tree_result = await db.execute(select(Tree).where(Tree.id == tree_id))
    tree = tree_result.scalar_one_or_none()
    if not tree:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Дерево не найдено")

    has_access = await access_service.check_tree_access(db, tree_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому дереву"
        )

    result = await person_service.add_person_to_tree(
        db=db,
        tree_id=tree_id,
        requester_id=current_user.id,
        person_in=person_in,
        force_create=force_create
    )
    return result


@router.post("/persons/{person_id}/photo", response_model=dict, status_code=status.HTTP_200_OK)
async def upload_person_photo(
        person_id: UUID,
        file: UploadFile = File(..., description="Фотография персоны (JPEG, PNG, WebP, макс. 5 МБ)"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Загружает фотографию для персоны.
    Старое фото (если было) автоматически удаляется.
    """
    # 1. Проверяем, что персона существует
    person_result = await db.execute(select(Person).where(Person.id == person_id))
    person = person_result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Персона не найдена")

    # 2. Проверяем права доступа
    has_access = await access_service.check_person_access(db, person_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой персоне"
        )

    # 3. Удаляем старое фото (если есть)
    if person.photo_url:
        photo_service.delete_photo(person.photo_url)

    # 4. Сохраняем новое фото
    photo_url = await photo_service.save_photo(file)

    # 5. Обновляем запись в БД
    person.photo_url = photo_url
    await db.commit()

    return {
        "message": "Фото успешно загружено",
        "photo_url": photo_url
    }


@router.delete("/persons/{person_id}/photo", response_model=dict)
async def delete_person_photo(
        person_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Удаляет фотографию персоны."""
    person_result = await db.execute(select(Person).where(Person.id == person_id))
    person = person_result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Персона не найдена")

    has_access = await access_service.check_person_access(db, person_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой персоне"
        )

    if person.photo_url:
        photo_service.delete_photo(person.photo_url)
        person.photo_url = None
        await db.commit()
        return {"message": "Фото успешно удалено"}

    return {"message": "У персоны не было фото"}