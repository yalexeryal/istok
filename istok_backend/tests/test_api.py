async def test_health_check(test_client):
    """Тест проверки работоспособности приложения."""
    response = await test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


async def test_register_and_login(test_client):
    """Тест регистрации и последующего входа пользователя."""
    # 1. Регистрация
    register_data = {
        "email": "test_user@istok.family",
        "password": "testpassword123",
        "full_name": "Тестовый Пользователь"
    }
    response = await test_client.post("/users/register", json=register_data)
    assert response.status_code in [201, 400]

    # 2. Вход в систему
    login_data = "username=test_user@istok.family&password=testpassword123"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = await test_client.post("/auth/login", content=login_data, headers=headers)

    assert response.status_code == 200
    json_response = response.json()
    assert "access_token" in json_response
    assert json_response["token_type"] == "bearer"


async def test_get_trees_unauthorized(test_client):
    """Тест, что без токена доступ к деревьям запрещен."""
    response = await test_client.get("/trees/")
    assert response.status_code == 401

