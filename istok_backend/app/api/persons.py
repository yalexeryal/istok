# -*- coding: utf-8 -*-
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.person import Person, GenderEnum
from app.models.tree_person import TreePerson
from app.models.user import User
from app.schemas.person import PersonCreate, PersonResponse, PersonUpdate, PersonSearchResponse
from app.services.access_service import check_tree_access

router = APIRouter(prefix="/persons/trees/{tree_id}", tags=["Persons"])

UPLOAD_DIR = Path("/app/app/uploads/photos")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ


def _validate_image(file: UploadFile) -> None:
    """Проверяет тип и размер файла."""
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла: {file.content_type}. Разрешены только изображения."
        )
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // 1024 // 1024} МБ"
        )


def _get_extension(filename: str) -> str:
    """Получает расширение файла."""
    return Path(filename).suffix.lower() if filename else ".jpg"


@router.get("/", response_model=list[PersonResponse])
async def get_tree_persons(
        tree_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получить всех персон дерева."""
    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")

    result = await db.execute(
        select(Person)
        .join(TreePerson, TreePerson.person_id == Person.id)
        .where(TreePerson.tree_id == tree_id)
        .order_by(Person.last_name, Person.first_name)
    )
    return result.scalars().all()


@router.post("/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(
        tree_id: UUID,
        person_data: PersonCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Создать новую персону в дереве."""
    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")

    person_id = uuid.uuid4()
    new_person = Person(
        id=person_id,
        first_name=person_data.first_name,
        last_name=person_data.last_name,
        maiden_name=person_data.maiden_name,
        middle_name=person_data.middle_name,
        birth_date=person_data.birth_date,
        birth_place=person_data.birth_place,
        death_date=person_data.death_date,
        death_place=person_data.death_place,
        burial_place=person_data.burial_place,
        gender=GenderEnum(person_data.gender) if person_data.gender else None,
        photo_url=person_data.photo_url,
        created_by=current_user.id
    )
    db.add(new_person)
    db.add(TreePerson(tree_id=tree_id, person_id=person_id, added_by=current_user.id))
    await db.commit()
    await db.refresh(new_person)
    return new_person


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
        tree_id: UUID,
        person_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получить персону по ID."""
    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")

    result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            TreePerson.tree_id == tree_id,
            TreePerson.person_id == Person.id
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Персона не найдена")
    return person


@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(
        tree_id: UUID,
        person_id: UUID,
        person_data: PersonUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Обновить данные персоны."""
    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")

    result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            TreePerson.tree_id == tree_id,
            TreePerson.person_id == Person.id
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Персона не найдена")

    update_data = person_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "gender" and value is not None:
            setattr(person, field, GenderEnum(value))
        else:
            setattr(person, field, value)

    await db.commit()
    await db.refresh(person)
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
        tree_id: UUID,
        person_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Удалить персону из дерева."""
    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")

    result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            TreePerson.tree_id == tree_id,
            TreePerson.person_id == Person.id
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Персона не найдена")

    # Удаляем фото если есть
    if person.photo_url:
        photo_path = UPLOAD_DIR / person.photo_url.split("/")[-1]
        if photo_path.exists():
            photo_path.unlink()

    await db.delete(person)
    await db.commit()


@router.get("/search", response_model=list[PersonSearchResponse])
async def search_persons(
        tree_id: UUID,
        q: str = "",
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Поиск персон по имени/фамилии."""
    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")

    search_term = f"%{q}%"
    result = await db.execute(
        select(Person)
        .join(TreePerson, TreePerson.person_id == Person.id)
        .where(
            TreePerson.tree_id == tree_id,
            (Person.first_name.ilike(search_term) | Person.last_name.ilike(search_term))
        )
        .order_by(Person.last_name, Person.first_name)
    )
    return result.scalars().all()


# === ФОТОГРАФИИ ПЕРСОН ===

@router.post("/{person_id}/photo", status_code=status.HTTP_200_OK)
async def upload_person_photo(
        tree_id: UUID,
        person_id: UUID,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Загрузить фотографию персоны."""
    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")

    # Проверяем существование персоны
    result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            TreePerson.tree_id == tree_id,
            TreePerson.person_id == Person.id
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Персона не найдена")

    # Валидация файла
    _validate_image(file)

    # Генерируем уникальное имя файла
    ext = _get_extension(file.filename)
    unique_filename = f"{person_id}{ext}"
    file_path = UPLOAD_DIR / unique_filename

    # Создаем директорию если не существует
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Удаляем старое фото если есть
    if person.photo_url:
        old_photo_path = UPLOAD_DIR / person.photo_url.split("/")[-1]
        if old_photo_path.exists():
            old_photo_path.unlink()

    # Сохраняем файл
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // 1024 // 1024} МБ"
        )

    with open(file_path, "wb") as f:
        f.write(content)

    # Обновляем URL в БД
    person.photo_url = f"uploads/photos/{unique_filename}"
    await db.commit()
    await db.refresh(person)

    return {
        "message": "Фото успешно загружено",
        "photo_url": person.photo_url
    }


@router.get("/{person_id}/photo")
async def get_person_photo(
        tree_id: UUID,
        person_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получить фотографию персоны."""
    from fastapi.responses import FileResponse

    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")

    result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            TreePerson.tree_id == tree_id,
            TreePerson.person_id == Person.id
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Персона не найдена")

    if not person.photo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фото не загружено")

    photo_path = UPLOAD_DIR / person.photo_url.split("/")[-1]
    if not photo_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл фото не найден на диске")

    return FileResponse(
        path=str(photo_path),
        media_type="image/jpeg",
        headers={"Content-Disposition": f"inline; filename={photo_path.name}"}
    )


@router.delete("/{person_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person_photo(
        tree_id: UUID,
        person_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Удалить фотографию персоны."""
    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")

    result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            TreePerson.tree_id == tree_id,
            TreePerson.person_id == Person.id
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Персона не найдена")

    if not person.photo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фото не загружено")

    # Удаляем файл с диска
    photo_path = UPLOAD_DIR / person.photo_url.split("/")[-1]
    if photo_path.exists():
        photo_path.unlink()

    # Очищаем поле в БД
    person.photo_url = None
    await db.commit()
