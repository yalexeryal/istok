from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.access_request import AccessRequest, RequestStatusEnum
from app.models.notification import Notification, NotificationTypeEnum
from app.models.tree_person import TreePerson
from app.models.person import Person
from app.models.tree import Tree
from app.models.user import User


async def get_pending_requests_for_tree_owner(
        db: AsyncSession,
        owner_id: UUID
) -> list[AccessRequest]:
    """Получает все ожидающие запросы для деревьев владельца"""
    # Находим все деревья владельца
    trees_result = await db.execute(
        select(Tree.id).where(Tree.owner_id == owner_id)
    )
    tree_ids = [row[0] for row in trees_result.all()]

    if not tree_ids:
        return []

    # Находим все ожидающие запросы для этих деревьев
    result = await db.execute(
        select(AccessRequest)
        .where(
            AccessRequest.tree_id.in_(tree_ids),
            AccessRequest.status == RequestStatusEnum.PENDING
        )
        .order_by(AccessRequest.created_at.desc())
    )
    return result.scalars().all()


async def process_access_request(
        db: AsyncSession,
        request_id: UUID,
        owner_id: UUID,
        action: str
) -> dict:
    """
    Обрабатывает запрос на доступ: подтверждает или отклоняет.
    Возвращает результат операции.
    """
    # 1. Находим запрос
    result = await db.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    access_request = result.scalar_one_or_none()

    if not access_request:
        raise ValueError("Запрос не найден")

    # 2. Проверяем, что дерево принадлежит текущему пользователю
    tree_result = await db.execute(
        select(Tree).where(Tree.id == access_request.tree_id)
    )
    tree = tree_result.scalar_one_or_none()

    if not tree or tree.owner_id != owner_id:
        raise ValueError("У вас нет прав на обработку этого запроса")

    # 3. Проверяем, что запрос ещё не обработан
    if access_request.status != RequestStatusEnum.PENDING:
        raise ValueError(f"Запрос уже обработан (статус: {access_request.status})")

    # 4. Получаем данные запрашивающего пользователя
    requester_result = await db.execute(
        select(User).where(User.id == access_request.requester_id)
    )
    requester = requester_result.scalar_one_or_none()

    if not requester:
        raise ValueError("Пользователь, отправивший запрос, не найден")

    # 5. Обрабатываем действие
    if action == "approve":
        # Подтверждаем запрос
        access_request.status = RequestStatusEnum.APPROVED

        # Если указана персона, добавляем её в дерево запрашивающего пользователя
        if access_request.person_id:
            # Проверяем, есть ли уже эта персона в дереве запрашивающего
            existing_tp = await db.execute(
                select(TreePerson).where(
                    TreePerson.tree_id == access_request.tree_id,
                    TreePerson.person_id == access_request.person_id
                )
            )

            if not existing_tp.scalar_one_or_none():
                # Добавляем персону в дерево запрашивающего
                new_tree_person = TreePerson(
                    tree_id=access_request.tree_id,
                    person_id=access_request.person_id,
                    added_by=owner_id  # Владелец дерева добавил
                )
                db.add(new_tree_person)

        # Создаём уведомление для запрашивающего пользователя
        notification = Notification(
            user_id=access_request.requester_id,
            type=NotificationTypeEnum.REQUEST_APPROVED,
            payload={
                "tree_id": str(access_request.tree_id),
                "tree_name": tree.name,
                "request_id": str(access_request.id)
            }
        )
        db.add(notification)

        await db.commit()

        return {
            "status": "approved",
            "message": f"Запрос подтверждён. Персона добавлена в дерево '{tree.name}'."
        }

    elif action == "reject":
        # Отклоняем запрос
        access_request.status = RequestStatusEnum.REJECTED

        # Создаём уведомление для запрашивающего пользователя
        notification = Notification(
            user_id=access_request.requester_id,
            type=NotificationTypeEnum.REQUEST_APPROVED,  # Можно создать отдельный тип
            payload={
                "tree_id": str(access_request.tree_id),
                "tree_name": tree.name,
                "request_id": str(access_request.id),
                "rejected": True
            }
        )
        db.add(notification)

        await db.commit()

        return {
            "status": "rejected",
            "message": f"Запрос отклонён."
        }

    else:
        raise ValueError(f"Неизвестное действие: {action}. Допустимые: 'approve', 'reject'")