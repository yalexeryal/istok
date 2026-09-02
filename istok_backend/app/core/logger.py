import sys
from loguru import logger
from app.core.config import get_settings

settings = get_settings()

# Убираем стандартный логгер loguru
logger.remove()

# Добавляем красивый консольный логгер для разработки
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO",
    colorize=True,
)

# Добавляем файловый логгер с ротацией (для продакшена)
logger.add(
    "logs/app.log",
    rotation="10 MB",  # Новый файл каждые 10 МБ
    retention="7 days",  # Храним логи 7 дней
    compression="zip",   # Сжимаем старые логи
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    serialize=False,  # Для продакшена можно поставить True (JSON-формат)
)

# Отдельный файл для ошибок
logger.add(
    "logs/error.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
)

def get_logger(name: str):
    """Получить логгер с указанием имени модуля."""
    return logger.bind(name=name)