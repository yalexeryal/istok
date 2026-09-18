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


@pytest.mark.asyncio
async def test_create_child_with_auto_lastname_and_relationship(client: AsyncClient):
    """
    Тест проверяет:
    1. Создание отца.
    2. Создание ребенка с указанием father_id, но БЕЗ указания last_name.
    3. Проверка, что ребенку автоматически подставилась фамилия отца.
    4. Проверка, что связь biological_parent была создана автоматически.
    """
    # 1. Создаем отца
    father_data = {"first_name": "Иван", "last_name": "Сидоров", "gender": "male", "tree_id": 1}
    res_father = await client.post("/persons/", json=father_data)
    assert res_father.status_code == 201
    father_id = res_father.json()["id"]

    # 2. Создаем ребенка без фамилии, но с father_id
    child_data = {
        "first_name": "Алексей",
        "gender": "male",
        "tree_id": 1,
        "father_id": father_id
    }
    res_child = await client.post("/persons/", json=child_data)
    assert res_child.status_code == 201
    child_id = res_child.json()["id"]

    # 3. Проверяем, что фамилия подставилась
    assert res_child.json()["last_name"] == "Сидоров", "Фамилия отца не была подставлена автоматически!"

    # 4. Проверяем, что связь создалась
    res_rels = await client.get(f"/relationships/persons/{child_id}")
    assert res_rels.status_code == 200
    rels = res_rels.json()

    assert len(rels) == 1, "Связь с отцом не была создана!"
    assert rels[0]["from_person_id"] == father_id
    assert rels[0]["to_person_id"] == child_id
    assert rels[0]["relationship_type"] == "biological_parent"


@pytest.mark.asyncio
async def test_auto_generate_patronymic(client: AsyncClient):
    """
    Тест проверяет автогенерацию отчества от отца для разных имен и полов.
    """
    # 1. Создаем отцов с разными именами
    # Иван (стандартное)
    res_f1 = await client.post("/persons/", json={"first_name": "Иван", "gender": "male", "tree_id": 1})
    f1_id = res_f1.json()["id"]

    # Дмитрий (на 'й')
    res_f2 = await client.post("/persons/", json={"first_name": "Дмитрий", "gender": "male", "tree_id": 1})
    f2_id = res_f2.json()["id"]

    # Никита (исключение)
    res_f3 = await client.post("/persons/", json={"first_name": "Никита", "gender": "male", "tree_id": 1})
    f3_id = res_f3.json()["id"]

    # 2. Создаем сына Ивана (должен стать Иванович)
    res_son = await client.post("/persons/", json={
        "first_name": "Алексей", "gender": "male", "tree_id": 1, "father_id": f1_id
    })
    assert res_son.json()["middle_name"] == "Иванович", f"Ожидался Иванович, получено {res_son.json()['middle_name']}"

    # 3. Создаем дочь Дмитрия (должна стать Дмитриевна)
    res_daughter = await client.post("/persons/", json={
        "first_name": "Анна", "gender": "female", "tree_id": 1, "father_id": f2_id
    })
    assert res_daughter.json()[
               "middle_name"] == "Дмитриевна", f"Ожидалась Дмитриевна, получено {res_daughter.json()['middle_name']}"

    # 4. Создаем сына Никиты (исключение, должен стать Никитич)
    res_son_nikita = await client.post("/persons/", json={
        "first_name": "Петр", "gender": "male", "tree_id": 1, "father_id": f3_id
    })
    assert res_son_nikita.json()[
               "middle_name"] == "Никитич", f"Ожидался Никитич, получено {res_son_nikita.json()['middle_name']}"


@pytest.mark.asyncio
async def test_patronymic_different_cultures(client: AsyncClient):
    """Тест генерации отчеств для разных культур."""

    # Русский
    res_f_ru = await client.post("/persons/",
                                 json={"first_name": "Иван", "gender": "male", "tree_id": 1, "culture": "ru"})
    f_ru_id = res_f_ru.json()["id"]

    res_son_ru = await client.post("/persons/", json={
        "first_name": "Алексей", "gender": "male", "tree_id": 1, "father_id": f_ru_id, "culture": "ru"
    })
    assert res_son_ru.json()["middle_name"] == "Иванович"

    # Украинский
    res_f_uk = await client.post("/persons/",
                                 json={"first_name": "Іван", "gender": "male", "tree_id": 1, "culture": "uk"})
    f_uk_id = res_f_uk.json()["id"]

    res_son_uk = await client.post("/persons/", json={
        "first_name": "Олексій", "gender": "male", "tree_id": 1, "father_id": f_uk_id, "culture": "uk"
    })
    assert res_son_uk.json()["middle_name"] == "Іванович"

    # Казахский
    res_f_kk = await client.post("/persons/",
                                 json={"first_name": "Асан", "gender": "male", "tree_id": 1, "culture": "kk"})
    f_kk_id = res_f_kk.json()["id"]

    res_son_kk = await client.post("/persons/", json={
        "first_name": "Болат", "gender": "male", "tree_id": 1, "father_id": f_kk_id, "culture": "kk"
    })
    assert "ұлы" in res_son_kk.json()["middle_name"]

    # Шведский
    res_f_sv = await client.post("/persons/",
                                 json={"first_name": "Erik", "gender": "male", "tree_id": 1, "culture": "sv"})
    f_sv_id = res_f_sv.json()["id"]

    res_son_sv = await client.post("/persons/", json={
        "first_name": "Lars", "gender": "male", "tree_id": 1, "father_id": f_sv_id, "culture": "sv"
    })
    assert res_son_sv.json()["middle_name"] == "Erikson"

    # Исландский
    res_f_is = await client.post("/persons/",
                                 json={"first_name": "Jón", "gender": "male", "tree_id": 1, "culture": "is"})
    f_is_id = res_f_is.json()["id"]

    res_daughter_is = await client.post("/persons/", json={
        "first_name": "Björk", "gender": "female", "tree_id": 1, "father_id": f_is_id, "culture": "is"
    })
    assert res_daughter_is.json()["middle_name"] == "Jóndóttir"


@pytest.mark.asyncio
async def test_sandbox_and_duplicate_detection(client: AsyncClient):
    """
    Тест проверяет:
    1. Новая персона попадает в песочницу (status=sandbox)
    2. Система находит похожих персон
    3. Можно подтвердить персону (перевести в confirmed)
    4. Можно слить с дубликатом (перевести в merged)
    """
    # 1. Создаем первую персону и подтверждаем её
    person1_data = {
        "first_name": "Иван",
        "last_name": "Петров",
        "birth_date": "1970-05-15",
        "birth_place": "Москва",
        "gender": "male",
        "tree_id": 1,
        "skip_duplicate_check": True  # Пропускаем проверку для первой
    }
    res1 = await client.post("/persons/", json=person1_data)
    assert res1.status_code == 201
    person1_id = res1.json()["id"]

    # Подтверждаем первую персону
    res_confirm1 = await client.post(f"/persons/{person1_id}/confirm")
    assert res_confirm1.status_code == 200
    assert res_confirm1.json()["status"] == "confirmed"

    # 2. Создаем вторую похожую персону (должна попасть в песочницу и найти дубликат)
    person2_data = {
        "first_name": "Иван",
        "last_name": "Петров",
        "birth_date": "1971-05-15",  # Разница в 1 год
        "birth_place": "Москва",
        "gender": "male",
        "tree_id": 1
    }
    res2 = await client.post("/persons/", json=person2_data)
    assert res2.status_code == 201
    person2_id = res2.json()["id"]

    # Проверяем, что вторая персона в песочнице
    assert res2.json()["status"] == "sandbox"

    # Проверяем, что нашли дубликат
    duplicates = res2.json().get("potential_duplicates", [])
    assert len(duplicates) > 0, "Дубликат не найден!"
    assert duplicates[0]["id"] == person1_id
    assert duplicates[0]["similarity_score"] >= 50

    # 3. Подтверждаем вторую персону (что это не дубликат)
    res_confirm2 = await client.post(f"/persons/{person2_id}/confirm")
    assert res_confirm2.status_code == 200
    assert res_confirm2.json()["status"] == "confirmed"

    # 4. Создаем третью похожую персону и сливаем с первой
    person3_data = {
        "first_name": "Иван",
        "last_name": "Петров",
        "birth_date": "1970-05-15",
        "birth_place": "Москва",
        "gender": "male",
        "tree_id": 1
    }
    res3 = await client.post("/persons/", json=person3_data)
    assert res3.status_code == 201
    person3_id = res3.json()["id"]

    # Сливаем третью с первой
    res_merge = await client.post(f"/persons/{person3_id}/merge/{person1_id}")
    assert res_merge.status_code == 200
    assert res_merge.json()["status"] == "merged"
    assert res_merge.json()["merged_into_id"] == person1_id

    # 5. Проверяем, что в списке confirmed только первая и вторая
    res_list = await client.get("/persons/?tree_id=1&status=confirmed")
    assert res_list.status_code == 200
    confirmed_persons = res_list.json()
    assert len(confirmed_persons) == 2
    confirmed_ids = [p["id"] for p in confirmed_persons]
    assert person1_id in confirmed_ids
    assert person2_id in confirmed_ids
    assert person3_id not in confirmed_ids  # Слитая не должна быть в списке