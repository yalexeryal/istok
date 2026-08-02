from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.relation import RelationCreate, RelationResponse
from app.services import relation_service
from app.models.user import User

router = APIRouter(prefix="/relations", tags=["Relations"])

@router.post("/", response_model=RelationResponse, status_code=status.HTTP_201_CREATED)
async def create_relation(
    relation_in: RelationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создает связь между двумя людьми.
    Автоматически добавляет события жизни (рождение ребенка, брак).
    """
    try:
        new_relation = await relation_service.create_relation(
            db=db,
            user_id=current_user.id,
            relation_in=relation_in
        )
        return new_relation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/person/{person_id}", response_model=list[RelationResponse])
async def get_person_relations(
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получает все связи для конкретного человека.
    """
    relations = await relation_service.get_person_relations(db, person_id)
    return relations