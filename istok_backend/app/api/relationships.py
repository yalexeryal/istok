"""
Роутер для управления родственными связями (Relationships).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.models.models import Person, Relationship
from app.schemas.schemas import RelationshipCreate, RelationshipResponse

router = APIRouter(prefix="/relationships", tags=["Relationships"])


@router.post("/", response_model=RelationshipResponse, status_code=201)
async def create_relationship(rel: RelationshipCreate, db: AsyncSession = Depends(get_db)):
    """
    Создание новой родственной связи между двумя персонами.
    """
    # Проверяем, что обе персоны существуют в базе
    res_from = await db.execute(select(Person).where(Person.id == rel.from_person_id))
    res_to = await db.execute(select(Person).where(Person.id == rel.to_person_id))

    if not res_from.scalar_one_or_none() or not res_to.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Одна из указанных персон не найдена")

    # Создаем связь
    db_rel = Relationship(**rel.model_dump())
    db.add(db_rel)
    await db.commit()
    await db.refresh(db_rel)
    return db_rel


@router.get("/persons/{person_id}", response_model=list[RelationshipResponse])
async def get_person_relationships(person_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение всех связей конкретной персоны.
    Возвращает связи, где персона является как инициатором (from), так и получателем (to).
    """
    # Проверяем, что персона существует
    res = await db.execute(select(Person).where(Person.id == person_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Персона не найдена")

    # Ищем связи в обе стороны (or_)
    stmt = select(Relationship).where(
        or_(
            Relationship.from_person_id == person_id,
            Relationship.to_person_id == person_id
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()