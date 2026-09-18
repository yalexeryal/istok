"""
Сервис для поиска дубликатов персон.
Ищет похожие записи по критериям: ФИО + год рождения (±1 год), место рождения.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import timedelta
from app.models.models import Person


async def find_potential_duplicates(
        db: AsyncSession,
        first_name: str,
        last_name: str | None = None,
        birth_date: str | None = None,
        birth_place: str | None = None,
        exclude_id: int | None = None
) -> list[Person]:
    """
    Ищет похожих персон по критериям:
    1. Имя + Фамилия + Год рождения (±1 год)
    2. Имя + Фамилия + Место рождения

    Args:
        db: Сессия БД
        first_name: Имя персоны
        last_name: Фамилия (опционально)
        birth_date: Дата рождения в формате YYYY-MM-DD (опционально)
        birth_place: Место рождения (опционально)
        exclude_id: ID персоны для исключения из поиска (опционально)

    Returns:
        Список похожих персон (только со статусом 'confirmed')
    """
    # Базовый запрос: только подтвержденные персоны
    query = select(Person).where(Person.status == "confirmed")

    # Исключаем саму персону (если это обновление)
    if exclude_id:
        query = query.where(Person.id != exclude_id)

    # Критерий 1: Имя + Фамилия
    conditions = [Person.first_name.ilike(f"%{first_name}%")]

    if last_name:
        conditions.append(
            or_(
                Person.last_name.ilike(f"%{last_name}%"),
                Person.maiden_name.ilike(f"%{last_name}%")
            )
        )

    # Критерий 2: Год рождения ±1 год
    if birth_date:
        from datetime import datetime
        birth_dt = datetime.strptime(birth_date, "%Y-%m-%d").date()
        year_minus_1 = birth_dt.replace(year=birth_dt.year - 1)
        year_plus_1 = birth_dt.replace(year=birth_dt.year + 1)

        conditions.append(
            and_(
                Person.birth_date >= year_minus_1,
                Person.birth_date <= year_plus_1
            )
        )

    # Критерий 3: Место рождения (если указано)
    if birth_place:
        conditions.append(Person.birth_place.ilike(f"%{birth_place}%"))

    # Применяем все условия
    query = query.where(and_(*conditions))

    result = await db.execute(query)
    return result.scalars().all()


async def calculate_similarity_score(person1: Person, person2: Person) -> float:
    """
    Вычисляет процент совпадения между двумя персонами (0-100).

    Критерии:
    - Имя: 30%
    - Фамилия: 30%
    - Год рождения: 20%
    - Место рождения: 20%
    """
    score = 0.0

    # Имя (30%)
    if person1.first_name.lower() == person2.first_name.lower():
        score += 30
    elif person1.first_name.lower() in person2.first_name.lower() or person2.first_name.lower() in person1.first_name.lower():
        score += 15

    # Фамилия (30%)
    if person1.last_name and person2.last_name:
        if person1.last_name.lower() == person2.last_name.lower():
            score += 30
        elif person1.last_name.lower() in person2.last_name.lower() or person2.last_name.lower() in person1.last_name.lower():
            score += 15

    # Год рождения (20%)
    if person1.birth_date and person2.birth_date:
        year_diff = abs(person1.birth_date.year - person2.birth_date.year)
        if year_diff == 0:
            score += 20
        elif year_diff == 1:
            score += 10

    # Место рождения (20%)
    if person1.birth_place and person2.birth_place:
        if person1.birth_place.lower() == person2.birth_place.lower():
            score += 20
        elif person1.birth_place.lower() in person2.birth_place.lower() or person2.birth_place.lower() in person1.birth_place.lower():
            score += 10

    return score