from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.access_request import AccessRequest, RequestStatusEnum
from app.models.tree import Tree
from app.models.user import User
from app.models.notification import Notification, NotificationTypeEnum
from typing import Optional


async def create_access_request(
    db: AsyncSession, 
    requester_id: UUID, 
    tree_id: UUID
) -> "AccessRequest":
    """Создает запрос на доступ к дереву."""
    from app.models.access_request import AccessRequest, RequestStatusEnum
    from app.models.tree import Tree
    from app.models.notification import Notification, NotificationTypeEnum
    
    # 1. Проверяем существование дерева
    tree_res = await db.execute(select(Tree).where(Tree.id == tree_id))
    tree = tree_res.scalar_one_or_none()
    if not tree:
        raise ValueError("Дерево не найдено")
    
    # 2. Проверка на дубликаты
    req_res = await db.execute(select(AccessRequest).where(
        AccessRequest.tree_id == tree_id,
        AccessRequest.requester_id == requester_id,
        AccessRequest.status.in_([RequestStatusEnum.PENDING, RequestStatusEnum.APPROVED])
    ))
    if req_res.scalar_one_or_none():
        raise ValueError("Запрос уже существует или уже одобрен")

    # 3. Создаем запрос (БЕЗ person_id, так как его нет в модели)
    new_req = AccessRequest(
        tree_id=tree_id,
        requester_id=requester_id,
        status=RequestStatusEnum.PENDING
    )
    db.add(new_req)
    await db.commit()
    await db.refresh(new_req)

    # 4. Создаем уведомление для владельца
    notification = Notification(
        user_id=tree.owner_id,
        type=NotificationTypeEnum.NEW_REQUEST,
        payload={
            "request_id": str(new_req.id), 
            "requester_id": str(requester_id), 
            "tree_name": tree.name
        },
        is_read=False
    )
    db.add(notification)
    await db.commit()
    
    return new_req

async def get_tree_requests(db: AsyncSession, tree_id: UUID, owner_id: UUID) -> list[dict]:
    tree_res = await db.execute(select(Tree).where(Tree.id == tree_id, Tree.owner_id == owner_id))
    if not tree_res.scalar_one_or_none():
        raise ValueError("Нет прав на просмотр запросов этого дерева")

    res = await db.execute(
        select(AccessRequest, User.full_name)
        .join(User, AccessRequest.requester_id == User.id)
        .where(AccessRequest.tree_id == tree_id, AccessRequest.status == RequestStatusEnum.PENDING)
        .order_by(AccessRequest.created_at.desc())
    )

    requests = []
    for row in res.all():
        req = row.AccessRequest
        requests.append({
            "id": req.id,
            "tree_id": req.tree_id,
            "requester_id": req.requester_id,
            "requester_name": row.full_name,
            "message": req.message,
            "status": req.status.value,
            "created_at": req.created_at
        })
    return requests


async def respond_to_request(db: AsyncSession, request_id: UUID, owner_id: UUID, action: str):
    res = await db.execute(
        select(AccessRequest, Tree.owner_id, Tree.name, Tree.id)
        .join(Tree, AccessRequest.tree_id == Tree.id)
        .where(AccessRequest.id == request_id)
    )
    row = res.first()
    if not row:
        raise ValueError("Запрос не найден")

    req, tree_owner_id, tree_name, tree_id = row

    if tree_owner_id != owner_id:
        raise ValueError("Нет прав на обработку этого запроса")

    if req.status != RequestStatusEnum.PENDING:
        raise ValueError("Запрос уже обработан")

    if action == "approve":
        req.status = RequestStatusEnum.APPROVED
    elif action == "reject":
        req.status = RequestStatusEnum.REJECTED
    else:
        raise ValueError("Недопустимое действие. Используйте 'approve' или 'reject'")

    await db.commit()
    return req