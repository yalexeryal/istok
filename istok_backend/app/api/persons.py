from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import Person
from app.schemas.schemas import PersonCreate, PersonResponse
from app.services.person_service import auto_create_life_events

router = APIRouter(prefix="/persons", tags=["Persons"])

@router.post("/", response_model=PersonResponse, status_code=201)
async def create_person(person: PersonCreate, db: AsyncSession = Depends(get_db)):
    db_person = Person(**person.model_dump())
    db.add(db_person)
    await db.flush()
    await auto_create_life_events(db, db_person)
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