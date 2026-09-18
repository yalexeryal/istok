"""
Роутер для управления персонами (Persons).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import Person
from app.schemas.schemas import PersonCreate, PersonResponse
from app.services.person_service import auto_create_life_events_and_relationships
from app.services.duplicate_checker import find_potential_duplicates, calculate_similarity_score

router = APIRouter(prefix="/persons", tags=["Persons"])


@router.post("/", response_model=PersonResponse, status_code=201)
async def create_person(person: PersonCreate, db: AsyncSession = Depends(get_db)):
    """
    Создание новой персоны.
    Автоматически проверяет на дубликаты и помещает в песочницу.
    """
    # Извлекаем ID родителей
    father_id = person.father_id
    mother_id = person.mother_id
    skip_check = person.skip_duplicate_check

    # Создаем объект Person
    person_data = person.model_dump(exclude={'father_id', 'mother_id', 'skip_duplicate_check'})
    person_data['status'] = 'sandbox'  # По умолчанию в песочницу

    db_person = Person(**person_data)
    db.add(db_person)
    await db.flush()

    # Вызываем сервис для бизнес-логики
    await auto_create_life_events_and_relationships(db, db_person, father_id, mother_id)

    # Проверяем на дубликаты (если не пропущено)
    potential_duplicates = []
    if not skip_check:
        duplicates = await find_potential_duplicates(
            db,
            first_name=person.first_name,
            last_name=person.last_name,
            birth_date=str(person.birth_date) if person.birth_date else None,
            birth_place=person.birth_place,
            exclude_id=db_person.id
        )

        # Вычисляем процент совпадения для каждого дубликата
        for dup in duplicates:
            score = await calculate_similarity_score(db_person, dup)
            if score >= 50:  # Порог совпадения 50%
                potential_duplicates.append({
                    "id": dup.id,
                    "full_name": dup.full_name_display,
                    "similarity_score": score,
                    "birth_date": str(dup.birth_date) if dup.birth_date else None,
                    "birth_place": dup.birth_place
                })

    await db.commit()
    await db.refresh(db_person)

    # Добавляем список дубликатов в ответ
    response = PersonResponse.model_validate(db_person)
    response.potential_duplicates = potential_duplicates

    return response


@router.get("/", response_model=list[PersonResponse])
async def get_persons(tree_id: int = 1, status: str = "confirmed", db: AsyncSession = Depends(get_db)):
    """
    Получение списка персон.
    По умолчанию возвращает только подтвержденные (confirmed).
    """
    query = select(Person).where(
        Person.tree_id == tree_id,
        Person.status == status,
        Person.merged_into_id == None  # Исключаем слитые
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/sandbox", response_model=list[PersonResponse])
async def get_sandbox_persons(tree_id: int = 1, db: AsyncSession = Depends(get_db)):
    """Получение списка персон в песочнице."""
    result = await db.execute(
        select(Person).where(
            Person.tree_id == tree_id,
            Person.status == "sandbox"
        )
    )
    return result.scalars().all()


@router.post("/{person_id}/confirm", response_model=PersonResponse)
async def confirm_person(person_id: int, db: AsyncSession = Depends(get_db)):
    """Подтвердить персону (перевести из песочницы в confirmed)."""
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(status_code=404, detail="Персона не найдена")

    if person.status != "sandbox":
        raise HTTPException(status_code=400, detail="Персона уже подтверждена или слита")

    person.status = "confirmed"
    await db.commit()
    await db.refresh(person)
    return person


@router.post("/{person_id}/merge/{target_id}", response_model=PersonResponse)
async def merge_person(person_id: int, target_id: int, db: AsyncSession = Depends(get_db)):
    """
    Слить персону с другой (target_id).
    person_id становится merged, target_id остается confirmed.
    """
    # Получаем обе персоны
    result1 = await db.execute(select(Person).where(Person.id == person_id))
    person = result1.scalar_one_or_none()

    result2 = await db.execute(select(Person).where(Person.id == target_id))
    target = result2.scalar_one_or_none()

    if not person or not target:
        raise HTTPException(status_code=404, detail="Одна из персон не найдена")

    if person.status == "merged":
        raise HTTPException(status_code=400, detail="Персона уже слита")

    # Помечаем как слитую
    person.status = "merged"
    person.merged_into_id = target_id

    await db.commit()
    await db.refresh(person)
    return person


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(person_id: int, db: AsyncSession = Depends(get_db)):
    """Получение данных одной персоны по ID."""
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Персона не найдена")
    return person