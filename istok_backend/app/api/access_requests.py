from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.access_request import AccessRequestResponse, AccessRequestAction
from app.services import access_request_service
from app.models.user import User
from app.models.person import Person
from app.models.tree import Tree
from sqlalchemy import select

router = APIRouter(prefix="/access-requests", tags=["Access Requests"])


@router.get("/", response_model=list[AccessRequestResponse])
async def get_my_pending_requests(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Получает все ожидающие запросы для деревьев текущего пользователя.
    """
    requests = await access_request_service.get_pending_requests_for_tree_owner(
        db, current_user.id
    )

    # Формируем ответ с дополнительными данными
    result = []
    for req in requests:
        # Получаем имя запрашивающего
        requester_result = await db.execute(
            select(User.full_name).where(User.id == req.requester_id)
        )
        requester_name = requester_result.scalar_one_or_none() or "Неизвестный пользователь"

        # Получаем название дерева
        tree_result = await db.execute(
            select(Tree.name).where(Tree.id == req.tree_id)
        )
        tree_name = tree_result.scalar_one_or_none() or "Неизвестное дерево"

        # Получаем имя персоны (если указана)
        person_name = None
        if req.person_id:
            person_result = await db.execute(
                select(Person.first_name, Person.last_name).where(Person.id == req.person_id)
            )
            person_row = person_result.first()
            if person_row:
                person_name = f"{person_row.last_name} {person_row.first_name}"

        result.append(AccessRequestResponse(
            id=req.id,
            requester_id=req.requester_id,
            requester_name=requester_name,
            tree_id=req.tree_id,
            tree_name=tree_name,
            person_id=req.person_id,
            person_name=person_name,
            status=req.status.value,
            created_at=req.created_at
        ))

    return result


@router.patch("/{request_id}", response_model=dict)
async def process_request(
        request_id: str,
        action_data: AccessRequestAction,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Подтверждает или отклоняет запрос на доступ.
    """
    try:
        result = await access_request_service.process_access_request(
            db=db,
            request_id=request_id,
            owner_id=current_user.id,
            action=action_data.action
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при обработке запроса"
        )