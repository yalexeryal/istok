from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from passlib.context import CryptContext

from app.core.database import engine, Base, AsyncSessionLocal
from app.models.models import User
from app.api import auth, persons, life_events

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "yalexer@istok.family"))
        if not result.scalar_one_or_none():
            hashed_pw = pwd_context.hash("yalexer123")
            new_user = User(email="yalexer@istok.family", hashed_password=hashed_pw, full_name="Администратор")
            session.add(new_user)
            await session.commit()
    yield


app = FastAPI(
    title="Istok API",
    description="API для системы ведения генеалогических деревьев 'Исток'",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(persons.router)
app.include_router(life_events.router)