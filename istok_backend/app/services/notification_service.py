from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
from app.models.notification import Notification, NotificationTypeEnum
from app.models.user import User
from app.models.person import Person
from app.models.tree import Tree


def format_notification_message(notification: Notification, user_name: str = "") -> str:
    """
    Формирует человекочитаемое сообщение для уведомления.
    """
    payload = notification.payload or {}

    if notification.type == NotificationTypeEnum.NEW_REQUEST:
        person_name = payload.get("person_name", "неизвестный человек")
        return f"Пользователь '{user_name}' запрашивает доступ к персоне '{person_name}' в вашем дереве."

    elif notification.type == NotificationTypeEnum.REQUEST_APPROVED:
        tree_name = payload.get("tree_name", "неизвестное дерево")
        if payload.get("rejected"):
            return f"Ваш запрос на доступ к дереву '{tree_name}' был отклонён."
        return f"Ваш запрос на доступ к дереву '{tree_name}' был подтверждён!"

    elif notification.type == NotificationTypeEnum.PERSON_FOUND:
        person_name = payload.get("person_name", "неизвестный человек")
        return f"Найдено совпадение для персоны '{person_name}' в базе данных."

    return "Новое уведомление"


async def get_user_notifications(
        db: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
) -> list[Notification]:
    """
    Получает уведомления пользователя.
    """
    query = select(Notification).where(Notification.user_id == user_id)

    if unread_only:
        query = query.where(Notification.is_read == False)

    query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


async def mark_notification_as_read(
        db: AsyncSession,
        notification_id: UUID,
        user_id: UUID
) -> bool:
    """
    Отмечает одно уведомление как прочитанное.
    Возвращает True, если уведомление найдено и обновлено.
    """
    # Проверяем, что уведомление принадлежит пользователю
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.is_read == False
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        return False

    notification.is_read = True
    await db.commit()
    return True


async def mark_all_notifications_as_read(
        db: AsyncSession,
        user_id: UUID
) -> int:
    """
    Отмечает все непрочитанные уведомления пользователя как прочитанные.
    Возвращает количество обновлённых записей.
    """
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        .values(is_read=True)
    )
    await db.commit()
    return result.rowcount


async def get_unread_count(
        db: AsyncSession,
        user_id: UUID
) -> int:
    """
    Возвращает количество непрочитанных уведомлений (для бейджа в UI).
    """
    result = await db.execute(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
    )
    return len(result.all())