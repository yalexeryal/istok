from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from app.core.config import get_settings
from app.api import users, persons, trees, auth, access_requests, notifications, relations, graph, life_events

settings = get_settings()

# Упрощенная схема безопасности только для Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

app = FastAPI(
    title=settings.APP_NAME,
    description="API для сервиса генеалогических деревьев Исток",
    version="0.1.0",
    # Добавляем схему безопасности для Swagger
    security=[{"oauth2": []}],
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

@app.get("/")
async def root():
    return {"message": "Добро пожаловать в Исток! API работает."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}