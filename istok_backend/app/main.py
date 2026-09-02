from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.core.config import get_settings

from app.api import (
    auth,
    users,
    trees,
    persons,
    access_requests,
    notifications,
    relations,
    graph,
    life_events,
    export
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
app.include_router(export.router)  # <-- ДОБАВЬТЕ ЭТУ СТРОКУ

# Монтируем папку uploads
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

@app.get("/")
async def root():
    return {"message": "Добро пожаловать в Исток! API работает."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}