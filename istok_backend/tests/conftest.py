"""
Конфигурация и фикстуры для pytest.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.database import engine, Base

@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """
    Создает таблицы в БД один раз перед всеми тестами.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Очистка после всех тестов
    await engine.dispose()

@pytest.fixture
async def client():
    """Асинхронный HTTP клиент для тестирования эндпоинтов."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac