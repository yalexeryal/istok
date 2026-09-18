"""
Тесты для проверки работы миграций Alembic.
"""
import pytest
from sqlalchemy import text
from app.core.database import engine


@pytest.mark.asyncio
async def test_alembic_migrations_work():
    """
    Тест проверяет, что таблицы существуют в БД (созданы через Alembic).
    """
    async with engine.begin() as conn:
        # Проверяем наличие таблицы persons
        result = await conn.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'persons')")
        )
        assert result.scalar() == True, "Таблица persons не существует!"

        # Проверяем наличие таблицы life_events
        result = await conn.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'life_events')")
        )
        assert result.scalar() == True, "Таблица life_events не существует!"

        # Проверяем наличие таблицы relationships
        result = await conn.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'relationships')")
        )
        assert result.scalar() == True, "Таблица relationships не существует!"

        # Проверяем наличие таблицы users
        result = await conn.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')")
        )
        assert result.scalar() == True, "Таблица users не существует!"

    print("✅ Все таблицы успешно созданы через Alembic!")