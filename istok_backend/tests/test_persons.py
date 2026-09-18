"""
Тесты для эндпоинтов и логики работы с персонами (Persons).
"""
import pytest
from httpx import AsyncClient
from app.models.models import EventTypeEnum


@pytest.mark.asyncio
async def test_create_person_and_auto_birth_event(client: AsyncClient):
    """
    Тест проверяет:
    1. Успешное создание персоны через API.
    2. Автоматическое создание события BIRTH при указании birth_date.
    3. Корректное получение созданной персоны по ID.
    """
    # 1. Данные для запроса
    person_data = {
        "first_name": "Иван",
        "last_name": "Петров",
        "birth_date": "1970-05-15",
        "birth_place": "Москва",
        "gender": "male",
        "tree_id": 1
    }

    # 2. Отправляем POST запрос на создание (ОБРАТИТЕ ВНИМАНИЕ на слэш в конце: "/persons/")
    response = await client.post("/persons/", json=person_data)

    # 3. Проверяем ответ API
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Иван"
    assert data["last_name"] == "Петров"
    assert "full_name_display" in data

    person_id = data["id"]

    # 4. Проверяем, что персона действительно сохранилась, через GET запрос
    response_get = await client.get(f"/persons/{person_id}")
    assert response_get.status_code == 200
    assert response_get.json()["id"] == person_id

    # 5. Проверяем, что событие рождения создалось автоматически
    response_events = await client.get(f"/persons/{person_id}/life-events")
    assert response_events.status_code == 200
    events = response_events.json()

    # Ищем событие BIRTH в списке
    birth_events = [e for e in events if e["event_type"] == EventTypeEnum.BIRTH.value]
    assert len(birth_events) == 1, "Событие рождения не было создано автоматически!"
    assert birth_events[0]["location"] == "Москва"


@pytest.mark.asyncio
async def test_get_persons_list(client: AsyncClient):
    """Тест проверяет получение списка персон."""
    # ОБРАТИТЕ ВНИМАНИЕ на слэш в конце: "/persons/"
    response = await client.get("/persons/?tree_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)