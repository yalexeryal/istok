import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.fixture(scope="module")
async def test_client():
    """Асинхронный клиент для тестирования API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac