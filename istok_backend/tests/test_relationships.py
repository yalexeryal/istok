"""
Тесты для эндпоинтов и логики работы с родственными связями (Relationships).
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_relationship(client: AsyncClient):
    """
    Тест проверяет:
    1. Создание двух персон (Отец и Сын).
    2. Создание связи biological_parent между ними.
    3. Получение списка связей для Отца и проверку наличия Сына.
    """
    # 1. Создаем Отца
    father_data = {"first_name": "Иван", "last_name": "Петров", "gender": "male", "tree_id": 1}
    res_father = await client.post("/persons/", json=father_data)
    assert res_father.status_code == 201
    father_id = res_father.json()["id"]

    # 2. Создаем Сына
    son_data = {"first_name": "Алексей", "last_name": "Петров", "gender": "male", "tree_id": 1}
    res_son = await client.post("/persons/", json=son_data)
    assert res_son.status_code == 201
    son_id = res_son.json()["id"]

    # 3. Создаем связь (Отец -> Сын)
    rel_data = {
        "from_person_id": father_id,
        "to_person_id": son_id,
        "relationship_type": "biological_parent",
        "is_current": True
    }
    res_rel = await client.post("/relationships/", json=rel_data)
    assert res_rel.status_code == 201
    assert res_rel.json()["relationship_type"] == "biological_parent"

    # 4. Получаем связи Отца
    res_get = await client.get(f"/relationships/persons/{father_id}")
    assert res_get.status_code == 200

    rels = res_get.json()
    assert len(rels) == 1
    assert rels[0]["to_person_id"] == son_id
    assert rels[0]["from_person_id"] == father_id

    # 5. Получаем связи Сына (должна быть та же связь, но в обратную сторону)
    res_get_son = await client.get(f"/relationships/persons/{son_id}")
    assert res_get_son.status_code == 200
    assert len(res_get_son.json()) == 1
