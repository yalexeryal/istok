from fastapi import FastAPI
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="API для сервиса генеалогических деревьев Исток",
    version="0.1.0",
)

@app.get("/")
async def root():
    return {"message": "Добро пожаловать в Исток! API работает."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}