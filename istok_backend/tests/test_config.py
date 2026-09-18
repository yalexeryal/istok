"""
Тест для проверки загрузки переменных окружения из .env файла.
"""
from app.core.config import settings


def test_settings_load_from_env():
    """
    Проверяет, что настройки загружаются именно из .env файла,
    а не из значений по умолчанию (которых теперь нет).
    """

    assert settings.SECRET_KEY == "MY_SUPER_SECRET_ENV_KEY_123", "Значение не прочитано из .env!"

    assert settings.DATABASE_URL == "postgresql+asyncpg://istok_user:istok_password@localhost:5433/istok_db"

    print(f"✅ Успех! Pydantic корректно прочитал SECRET_KEY из .env: {settings.SECRET_KEY}")