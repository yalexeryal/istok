import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException, status

# Путь к папке загрузок (относительно корня проекта)
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Разрешенные типы файлов
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 МБ


async def save_photo(file: UploadFile) -> str:
    """
    Сохраняет загруженное фото на диск.
    Возвращает относительный путь к файлу (для сохранения в БД).
    """
    # 1. Проверяем тип файла
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла. Разрешены: JPEG, PNG, WebP. Получено: {file.content_type}"
        )

    # 2. Проверяем размер файла
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл слишком большой. Максимум: 5 МБ. Ваш файл: {len(contents) / 1024 / 1024:.2f} МБ"
        )

    # 3. Генерируем уникальное имя файла
    extension = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename

    # 4. Сохраняем файл
    with open(file_path, "wb") as f:
        f.write(contents)

    # 5. Возвращаем относительный путь (для хранения в БД)
    return f"/uploads/{unique_filename}"


def delete_photo(photo_url: str) -> bool:
    """
    Удаляет старое фото с диска (если оно есть).
    """
    if not photo_url or not photo_url.startswith("/uploads/"):
        return False

    filename = photo_url.replace("/uploads/", "")
    file_path = UPLOAD_DIR / filename

    if file_path.exists():
        file_path.unlink()
        return True
    return False