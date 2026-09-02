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
from app.core.logger import get_logger

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time
from fastapi.middleware.cors import CORSMiddleware


logger = get_logger("main")

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

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Исток API запускается...")
    logger.info(f"📊 База данных: {settings.DATABASE_URL[:30]}...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Исток API останавливается")





class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000

        # Логируем каждый запрос
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms"
        )

        return response


# Добавьте middleware ПЕРЕД другими middleware
app.add_middleware(RequestLoggingMiddleware)

from fastapi.middleware.cors import CORSMiddleware

# Настройки CORS
origins = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server
    "http://localhost:8080",  # Vue dev server
    # В продакшене добавьте ваш домен:
    # "https://istok.yourdomain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Разрешенные домены
    allow_credentials=True,  # Разрешить куки и авторизацию
    allow_methods=["*"],     # Разрешить все HTTP методы
    allow_headers=["*"],     # Разрешить все заголовки
)