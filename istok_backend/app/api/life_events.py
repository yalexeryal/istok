from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import LifeEvent
from app.schemas.schemas import LifeEventResponse

router = APIRouter(prefix="/persons", tags=["LifeEvents"])

@router.get("/{person_id}/life-events", response_model=list[LifeEventResponse])
async def get_person_life_events(person_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LifeEvent).where(LifeEvent.person_id == person_id).order_by(LifeEvent.event_date)
    )
    return result.scalars().all()