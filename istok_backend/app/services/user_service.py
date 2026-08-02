import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserCreate


def get_password_hash(password: str) -> str:
    """Хеширует пароль с использованием bcrypt. Учитывает лимит в 72 байта."""
    # Кодируем в байты, обрезаем до 72 байт (лимит bcrypt), хешируем
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет совпадение пароля с хешем (понадобится для логина)"""
    pwd_bytes = plain_password.encode('utf-8')[:72]
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode('utf-8'))


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Ищет пользователя по email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """Создает нового пользователя в базе данных"""
    existing_user = await get_user_by_email(db, user_in.email)
    if existing_user:
        raise ValueError("Пользователь с таким email уже существует")

    hashed_password = get_password_hash(user_in.password)

    new_user = User(
        email=user_in.email,
        password_hash=hashed_password,
        full_name=user_in.full_name
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user