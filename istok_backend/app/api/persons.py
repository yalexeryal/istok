# -*- coding: utf-8 -*-
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.person import Person, GenderEnum
from app.models.tree_person import TreePerson
from app.models.user import User
from app.models.relation import Relation, RelationTypeEnum
from app.models.life_event import LifeEvent
from app.schemas.person import PersonCreate, PersonResponse, PersonUpdate, PersonSearchResponse
from app.services.access_service import check_tree_access

router = APIRouter(prefix="/persons/trees/{tree_id}", tags=["Persons"])

UPLOAD_DIR = Path("/app/app/uploads/photos")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def _validate_image(file: UploadFile) -> None:
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый тип файла. Разрешены только изображения."
        )


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lower() if filename else ".jpg"


# === СПИСОК ПЕРСОН ===

@router.get("/", response_model=list[PersonResponse])
async def get_tree_persons(
    tree_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not await check_tree_access(db, tree_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к дереву")
    
    result = await db.execute(
        select(Person)
        .join(TreePerson, TreePerson.person_id == Person.id)
        .where(TreePerson.tree_id == tree_id)
        .order_by(Person.last_name, Person.first_name)
    )
    return result.scalars().all()


# === ПОИСК ПЕРСОН (должен быть ПЕРЕД /{person_id}) ===

@router.get("/search", response_model=list[PersonSearchResponse])
async def search_persons(
    tree_id: UUID,
    q: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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


# === ДЕТАЛИ ПЕРСОНЫ СО СВЯЗЯМИ (ДОЛЖЕН БЫТЬ ПЕРЕД /{person_id} !!!) ===

@router.get("/{person_id}/details")
async def get_person_details(
    tree_id: UUID,
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить персону с полной информацией о связях."""
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
    
    all_persons_result = await db.execute(
        select(Person)
        .join(TreePerson, TreePerson.person_id == Person.id)
        .where(TreePerson.tree_id == tree_id)
    )
    all_persons = list(all_persons_result.scalars().all())
    person_dict = {p.id: p for p in all_persons}
    
    person_ids = [p.id for p in all_persons]
    relations_result = await db.execute(
        select(Relation).where(
            (Relation.person_1_id.in_(person_ids)) |
            (Relation.person_2_id.in_(person_ids))
        )
    )
    relations = list(relations_result.scalars().all())
    
    def person_to_dict(p: Person) -> dict:
        return {
            "id": str(p.id),
            "first_name": p.first_name,
            "last_name": p.last_name,
            "maiden_name": p.maiden_name,
            "middle_name": p.middle_name,
            "gender": str(p.gender.value) if p.gender else None,
            "birth_date": p.birth_date.isoformat() if p.birth_date else None,
            "death_date": p.death_date.isoformat() if p.death_date else None,
        }
    
    parents = []
    for rel in relations:
        if rel.type == RelationTypeEnum.PARENT_CHILD and rel.person_2_id == person_id:
            parent = person_dict.get(rel.person_1_id)
            if parent:
                parents.append(person_to_dict(parent))
    
    spouse = None
    for rel in relations:
        if rel.type == RelationTypeEnum.SPOUSE:
            if rel.person_1_id == person_id:
                sp = person_dict.get(rel.person_2_id)
                if sp:
                    spouse = person_to_dict(sp)
                    break
            elif rel.person_2_id == person_id:
                sp = person_dict.get(rel.person_1_id)
                if sp:
                    spouse = person_to_dict(sp)
                    break
    
    children = []
    for rel in relations:
        if rel.type == RelationTypeEnum.PARENT_CHILD and rel.person_1_id == person_id:
            child = person_dict.get(rel.person_2_id)
            if child:
                children.append(person_to_dict(child))
    
    parent_ids = {rel.person_1_id for rel in relations if rel.type == RelationTypeEnum.PARENT_CHILD and rel.person_2_id == person_id}
    siblings = []
    seen_sibling_ids = set()
    if parent_ids:
        for rel in relations:
            if rel.type == RelationTypeEnum.PARENT_CHILD and rel.person_1_id in parent_ids:
                sid = rel.person_2_id
                if sid != person_id and sid not in seen_sibling_ids:
                    seen_sibling_ids.add(sid)
                    sibling = person_dict.get(sid)
                    if sibling:
                        siblings.append(person_to_dict(sibling))
    
    events_result = await db.execute(
        select(LifeEvent).where(LifeEvent.person_id == person_id)
    )
    events = list(events_result.scalars().all())
    events_data = [
        {
            "id": str(event.id),
            "event_type": event.event_type,
            "date": event.date.isoformat() if event.date else None,
            "place": event.place,
            "description": event.description,
            "date_approx": getattr(event, 'date_approx', False),
        }
        for event in events
    ]
    
    return {
        "person": {
            "id": str(person.id),
            "first_name": person.first_name,
            "last_name": person.last_name,
            "maiden_name": person.maiden_name,
            "middle_name": person.middle_name,
            "birth_date": person.birth_date.isoformat() if person.birth_date else None,
            "birth_place": person.birth_place,
            "death_date": person.death_date.isoformat() if person.death_date else None,
            "death_place": person.death_place,
            "burial_place": getattr(person, 'burial_place', None),
            "gender": str(person.gender.value) if person.gender else None,
            "photo_url": person.photo_url,
        },
        "parents": parents,
        "spouse": spouse,
        "children": children,
        "siblings": siblings,
        "events": events_data,
    }


# === ФОТО ПЕРСОНЫ (ДОЛЖНЫ БЫТЬ ПЕРЕД /{person_id} !!!) ===

@router.post("/{person_id}/photo", status_code=status.HTTP_200_OK)
async def upload_person_photo(
    tree_id: UUID,
    person_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    
    _validate_image(file)
    
    ext = _get_extension(file.filename)
    unique_filename = f"{person_id}{ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    if person.photo_url:
        old_photo_path = UPLOAD_DIR / person.photo_url.split("/")[-1]
        if old_photo_path.exists():
            old_photo_path.unlink()
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл слишком большой. Максимум 10 МБ"
        )
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    person.photo_url = f"uploads/photos/{unique_filename}"
    await db.commit()
    await db.refresh(person)
    
    return {"message": "Фото успешно загружено", "photo_url": person.photo_url}


@router.get("/{person_id}/photo")
async def get_person_photo(
    tree_id: UUID,
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл фото не найден")
    
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
    if photo_path.exists():
        photo_path.unlink()
    
    person.photo_url = None
    await db.commit()


# === CRUD ПЕРСОН (в конце, так как /{person_id} перехватывает всё) ===

@router.post("/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(
    tree_id: UUID,
    person_data: PersonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    
    if person.photo_url:
        photo_path = UPLOAD_DIR / person.photo_url.split("/")[-1]
        if photo_path.exists():
            photo_path.unlink()
    
    await db.delete(person)
    await db.commit()