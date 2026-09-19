"""
Сервис для проверки прав доступа к деревьям и персонам.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import TreeCollaborator, CollaboratorRoleEnum, Person


async def check_tree_access(
        db: AsyncSession,
        tree_id: int,
        user_id: int,
        required_role: CollaboratorRoleEnum = CollaboratorRoleEnum.VIEWER
) -> TreeCollaborator:
    """
    Проверяет, имеет ли пользователь доступ к дереву с требуемой ролью.

    Args:
        db: Сессия БД
        tree_id: ID дерева
        user_id: ID пользователя
        required_role: Требуемая роль (VIEWER, EDITOR, CO_EDITOR, OWNER)

    Returns:
        Объект TreeCollaborator

    Raises:
        HTTPException: Если доступ запрещён
    """
    # Определяем приоритет ролей
    role_hierarchy = {
        CollaboratorRoleEnum.VIEWER: 0,
        CollaboratorRoleEnum.EDITOR: 1,
        CollaboratorRoleEnum.CO_EDITOR: 2,
        CollaboratorRoleEnum.OWNER: 3
    }

    # Ищем запись о соавторстве
    result = await db.execute(
        select(TreeCollaborator).where(
            TreeCollaborator.tree_id == tree_id,
            TreeCollaborator.user_id == user_id
        )
    )
    collaborator = result.scalar_one_or_none()

    if not collaborator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому дереву"
        )

    # Проверяем, что роль пользователя не ниже требуемой
    if role_hierarchy[collaborator.role] < role_hierarchy[required_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Требуется роль {required_role.value} или выше"
        )

    return collaborator


async def check_person_edit_access(
        db: AsyncSession,
        person_id: int,
        user_id: int
) -> bool:
    """
    Проверяет, может ли пользователь редактировать персону.

    Args:
        db: Сессия БД
        person_id: ID персоны
        user_id: ID пользователя

    Returns:
        True если может редактировать, иначе False
    """
    # Получаем персону
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()

    if not person:
        return False

    # Проверяем доступ к дереву с ролью EDITOR или выше
    try:
        await check_tree_access(db, person.tree_id, user_id, CollaboratorRoleEnum.EDITOR)
        return True
    except HTTPException:
        return False