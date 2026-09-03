# Используем стабильный slim-образ Python
FROM python:3.12-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off

# Устанавливаем системные зависимости (если нужны, например, для psycopg2 или build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для безопасности (не root)
RUN useradd -m -u 1000 istok_user

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install uvicorn[standard] gunicorn

# Копируем код проекта
COPY --chown=istok_user:istok_user . .

# Создаем папку для логов и меняем владельца
RUN mkdir -p /app/logs && chown -R istok_user:istok_user /app

# Переключаемся на небезопасного пользователя
USER istok_user

# Запускаем приложение через Gunicorn с Uvicorn workers (для продакшена)
# 4 воркера обычно достаточно для начала, можно масштабировать
CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]