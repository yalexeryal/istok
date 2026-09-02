from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from pathlib import Path

from app.api import (
    auth,
    users,
    trees,
    persons,
    access_requests,
    notifications,
    relations,
    graph,
    life_events
)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="API для сервиса генеалогических деревьев Исток",
    version="0.1.0",
)

# Подключаем все роутеры
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trees.router)
app.include_router(persons.router)
app.include_router(access_requests.router)
app.include_router(notifications.router)
app.include_router(relations.router)
app.include_router(graph.router)
app.include_router(life_events.router)

# Монтируем папку uploads для отдачи загруженных файлов
uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/")
async def root():
    return {"message": "Добро пожаловать в Исток! API работает."}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}