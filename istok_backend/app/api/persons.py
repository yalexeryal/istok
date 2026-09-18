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

router = APIRouter(prefix="/persons", tags=["Persons"])


@router.post("/", response_model=PersonResponse, status_code=201)
async def create_person(person: PersonCreate, db: AsyncSession = Depends(get_db)):
    """
    Создание новой персоны.
    Автоматически создает события жизни, связи с родителями и подставляет фамилию отца.
    """
    # Извлекаем ID родителей, так как их нет в модели SQLAlchemy Person
    father_id = person.father_id
    mother_id = person.mother_id

    # Создаем объект Person, исключая поля, которых нет в модели
    person_data = person.model_dump(exclude={'father_id', 'mother_id'})
    db_person = Person(**person_data)

    db.add(db_person)
    await db.flush()  # Получаем db_person.id для использования в сервисе

    # Вызываем сервис для выполнения всей бизнес-логики
    await auto_create_life_events_and_relationships(db, db_person, father_id, mother_id)

    await db.commit()
    await db.refresh(db_person)
    return db_person


@router.get("/", response_model=list[PersonResponse])
async def get_persons(tree_id: int = 1, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Person).where(Person.tree_id == tree_id))
    return result.scalars().all()


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(person_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Персона не найдена")
    return person