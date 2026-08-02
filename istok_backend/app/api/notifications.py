from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.notification import NotificationResponse, MarkAsReadResponse
from app.services import notification_service
from app.models.user import User
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(
        unread_only: bool = Query(False, description="Показать только непрочитанные"),
        limit: int = Query(50, ge=1, le=100, description="Количество уведомлений"),
        offset: int = Query(0, ge=0, description="Смещение для пагинации"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Получает список уведомлений текущего пользователя.
    """
    notifications = await notification_service.get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset
    )

    # Формируем ответ с человекочитаемыми сообщениями
    result = []
    for notif in notifications:
        # Получаем имя пользователя для формирования сообщения
        # (для NEW_REQUEST — это имя запрашивающего, для остальных — имя текущего пользователя)
        user_name = current_user.full_name

        if notif.type.value == "new_request" and notif.payload:
            requester_id = notif.payload.get("requester_id")
            if requester_id:
                requester_result = await db.execute(
                    select(User.full_name).where(User.id == requester_id)
                )
                user_name = requester_result.scalar_one_or_none() or user_name

        message = notification_service.format_notification_message(notif, user_name)

        result.append(NotificationResponse(
            id=notif.id,
            type=notif.type.value,
            message=message,
            payload=notif.payload,
            is_read=notif.is_read,
            created_at=notif.created_at
        ))

    return result


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Возвращает количество непрочитанных уведомлений (для бейджа в UI).
    """
    count = await notification_service.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.patch("/{notification_id}/read", response_model=dict)
async def mark_as_read(
        notification_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Отмечает одно уведомление как прочитанное.
    """
    success = await notification_service.mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Уведомление не найдено или уже прочитано"
        )

    return {"message": "Уведомление отмечено как прочитанное"}


@router.patch("/mark-all-read", response_model=MarkAsReadResponse)
async def mark_all_as_read(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Отмечает все непрочитанные уведомления как прочитанные.
    """
    count = await notification_service.mark_all_notifications_as_read(
        db=db,
        user_id=current_user.id
    )

    return MarkAsReadResponse(
        marked_count=count,
        message=f"Отмечено уведомлений как прочитанных: {count}"
    )