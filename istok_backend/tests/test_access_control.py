"""
Тесты для системы прав доступа и запросов на изменения.
"""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.models import User


async def _create_test_user(email_prefix: str, full_name: str) -> int:
    """
    Вспомогательная функция для надежного создания тестового пользователя
    с гарантированно уникальным ID, избегая проблем с sequence.
    """
    async with AsyncSessionLocal() as db:
        # Находим текущий максимальный ID
        res = await db.execute(select(func.max(User.id)))
        max_id = res.scalar() or 0
        new_id = max_id + 1

        unique_email = f"{email_prefix}_{uuid.uuid4().hex[:8]}@test.com"
        new_user = User(id=new_id, email=unique_email, hashed_password="hash", full_name=full_name)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user.id


@pytest.mark.asyncio
async def test_create_tree_and_add_collaborator(client: AsyncClient):
    """
    Тест проверяет:
    1. Создание нового дерева
    2. Добавление соавтора с ролью editor
    3. Получение списка соавторов дерева
    """
    # 0. Создаем второго пользователя в БД надежно
    test_user_id = await _create_test_user("collab", "Collab User")

    # 1. Создаём дерево
    tree_data = {"name": "Тестовое дерево Права", "description": "Тест прав доступа"}
    res_tree = await client.post("/trees/", json=tree_data)
    assert res_tree.status_code == 201, f"Не удалось создать дерево: {res_tree.text}"
    tree_id = res_tree.json()["id"]

    # 2. Добавляем соавтора с ролью editor
    collaborator_data = {
        "user_id": test_user_id,
        "role": "editor",
        "can_invite": False
    }
    res_collab = await client.post(f"/trees/{tree_id}/collaborators", json=collaborator_data)
    assert res_collab.status_code == 201, f"Не удалось добавить соавтора: {res_collab.text}"
    assert res_collab.json()["role"] == "editor"
    assert res_collab.json()["tree_id"] == tree_id

    # 3. Получаем список соавторов
    res_collabs = await client.get(f"/trees/{tree_id}/collaborators")
    assert res_collabs.status_code == 200
    collaborators = res_collabs.json()

    # Должно быть 2 соавтора: владелец (user_id=1) и редактор (test_user_id)
    assert len(collaborators) == 2, f"Ожидалось 2 соавтора, получено {len(collaborators)}"

    # Проверяем роли
    roles = {c["user_id"]: c["role"] for c in collaborators}
    assert roles[1] == "owner", "Пользователь 1 должен быть владельцем"
    assert roles[test_user_id] == "editor", f"Пользователь {test_user_id} должен быть редактором"


@pytest.mark.asyncio
async def test_change_request_workflow(client: AsyncClient):
    """
    Тест проверяет полный цикл запроса на изменение (авто-одобрение для владельца).
    """
    # 1. Создаём дерево
    tree_data = {"name": "Тестовое дерево Запросы", "description": "Тест запросов"}
    res_tree = await client.post("/trees/", json=tree_data)
    assert res_tree.status_code == 201
    tree_id = res_tree.json()["id"]

    # 2. Создаём персону
    person_data = {
        "first_name": "ТестИванЗапрос",
        "last_name": "ТестПетровЗапрос",
        "birth_date": "1970-05-15",
        "gender": "male",
        "tree_id": tree_id,
        "skip_duplicate_check": True
    }
    res_person = await client.post("/persons/", json=person_data)
    assert res_person.status_code == 201
    person_id = res_person.json()["id"]

    # 3. Подтверждаем персону
    await client.post(f"/persons/{person_id}/confirm")

    # 4. Создаём запрос на изменение (от имени владельца, поэтому сразу approved)
    change_data = {
        "person_id": person_id,
        "change_type": "update",
        "proposed_data": {"birth_place": "Санкт-Петербург"}
    }
    res_change = await client.post("/change-requests/", json=change_data)
    assert res_change.status_code == 201, f"Не удалось создать запрос: {res_change.text}"
    assert res_change.json()["status"] == "approved"

    # 5. Проверяем, что изменения применились к персоне
    res_person_updated = await client.get(f"/persons/{person_id}")
    assert res_person_updated.status_code == 200
    assert res_person_updated.json()["birth_place"] == "Санкт-Петербург"


@pytest.mark.asyncio
async def test_change_request_rejection(client: AsyncClient):
    """
    Тест проверяет отклонение запроса на изменение от пользователя БЕЗ прав.
    """
    # 0. Создаем пользователя без прав для этого теста надежно
    rejecter_user_id = await _create_test_user("rejecter", "Rejecter User")

    # 1. Создаём дерево и персону
    tree_data = {"name": "Тестовое дерево Отклонение", "description": "Тест отклонения"}
    res_tree = await client.post("/trees/", json=tree_data)
    assert res_tree.status_code == 201
    tree_id = res_tree.json()["id"]

    person_data = {
        "first_name": "ТестИванОтклон",
        "last_name": "ТестПетровОтклон",
        "birth_date": "1980-06-20",
        "gender": "male",
        "tree_id": tree_id,
        "skip_duplicate_check": True
    }
    res_person = await client.post("/persons/", json=person_data)
    assert res_person.status_code == 201
    person_id = res_person.json()["id"]

    # Подтверждаем персону
    await client.post(f"/persons/{person_id}/confirm")

    # 2. Создаём запрос на изменение ОТ ИМЕНИ ПОЛЬЗОВАТЕЛЯ БЕЗ ПРАВ
    change_data = {
        "person_id": person_id,
        "change_type": "update",
        "proposed_data": {"death_place": "Москва"},
        "requested_by_id": rejecter_user_id
    }
    res_change = await client.post("/change-requests/", json=change_data)
    assert res_change.status_code == 201, f"Не удалось создать запрос: {res_change.text}"
    assert res_change.json()["status"] == "pending", "Запрос должен остаться в ожидании"
    change_request_id = res_change.json()["id"]

    # 3. Отклоняем запрос (от имени владельца, id=1)
    res_reject = await client.post(
        f"/change-requests/{change_request_id}/respond?status=reject&comment=Неверные данные"
    )
    assert res_reject.status_code == 200, f"Не удалось отклонить запрос: {res_reject.text}"
    assert res_reject.json()["status"] == "rejected"
    assert res_reject.json()["response_comment"] == "Неверные данные"

    # 4. Проверяем, что данные персоны не изменились
    res_person_check = await client.get(f"/persons/{person_id}")
    assert res_person_check.status_code == 200
    assert res_person_check.json()["death_place"] is None, \
        "Место смерти не должно было быть установлено после отклонения"


@pytest.mark.asyncio
async def test_get_user_trees(client: AsyncClient):
    """
    Тест проверяет получение списка деревьев пользователя.
    """
    # Создаём несколько деревьев
    for i in range(3):
        tree_data = {"name": f"Дерево {i}", "description": f"Описание {i}"}
        res = await client.post("/trees/", json=tree_data)
        assert res.status_code == 201

    # Получаем список деревьев
    res_trees = await client.get("/trees/")
    assert res_trees.status_code == 200
    trees_list = res_trees.json()

    # Должно быть как минимум 3 дерева
    assert len(trees_list) >= 3, f"Ожидалось минимум 3 дерева, получено {len(trees_list)}"