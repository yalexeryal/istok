from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from passlib.context import CryptContext

# ВАЖНО: Убедитесь, что AsyncSessionLocal импортирован здесь!
from database import engine, Base, AsyncSessionLocal, get_db
from models import User
from config import settings

app = FastAPI(title="Istok API")

# Разрешаем CORS для всех источников (для локальной разработки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Модель запроса для входа
class LoginRequest(BaseModel):
    username: str
    password: str


# Создаем таблицы и тестового пользователя при запуске
@app.on_event("startup")
async def startup():
    # 1. Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Создаем тестового пользователя, если его нет
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "yalexer@istok.family"))
        if not result.scalar_one_or_none():
            hashed_pw = pwd_context.hash("yalexer123")
            new_user = User(email="yalexer@istok.family", hashed_password=hashed_pw)
            session.add(new_user)
            await session.commit()


@app.get("/")
async def root():
    return {"message": "Hello from Istok API"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/auth/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Ищем пользователя по email (который приходит в поле username)
    result = await db.execute(select(User).where(User.email == request.username))
    user = result.scalar_one_or_none()

    # Проверяем существование пользователя и корректность пароля
    if not user or not pwd_context.verify(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Возвращаем успешный ответ с тестовым токеном
    return {
        "access_token": "fake-jwt-token-for-testing",
        "token_type": "bearer",
        "message": "Успешный вход!"
    }