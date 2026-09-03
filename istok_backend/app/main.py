from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.core.config import get_settings
from app.core.logger import get_logger
from fastapi.middleware.cors import CORSMiddleware

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
    export,
    import_router  # <-- Импортируем роутер импорта
)

logger = get_logger("main")
settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="API для сервиса генеалогических деревьев Исток",
    version="0.1.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Можно изменить на конкретные домены в продакшене
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем все роутеры
app.include_router(auth.router, tags=["Auth"])
app.include_router(users.router, tags=["Users"])
app.include_router(trees.router, tags=["Trees"])
app.include_router(persons.router, tags=["Persons"])
app.include_router(relations.router, tags=["Relations"])
app.include_router(access_requests.router, tags=["Access Requests"])
app.include_router(notifications.router, tags=["Notifications"])
app.include_router(graph.router, tags=["Graph"])
app.include_router(life_events.router, tags=["Life Events"])
app.include_router(export.router, tags=["Export"])
app.include_router(import_router.router, tags=["Import"])

@app.get("/", tags=["default"])
def root():
    return {"message": "Welcome to Istok API"}

@app.get("/health", tags=["default"])
def health_check():
    return {"status": "healthy"}

# Монтирование папки для загруженных файлов
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")