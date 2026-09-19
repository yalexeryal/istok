# Техническое задание: Media Vault & Custodianship
## Модуль безопасного хранения медиафайлов и неизменяемого наследования

**Версия документа:** 1.0  
**Дата:** 19 сентября 2026  
**Статус:** На согласовании с командой безопасности  
**Проект:** Исток (генеалогическая платформа)

---

## 📋 Содержание

1. [Введение и обоснование](#1-введение-и-обоснование)
2. [Цели и ограничения](#2-цели-и-ограничения)
3. [Архитектура решения](#3-архитектура-решения)
4. [Модели данных](#4-модели-данных)
5. [API спецификация](#5-api-спецификация)
6. [Система наследования (Custodianship)](#6-система-наследования-custodianship)
7. [Безопасность и аудит](#7-безопасность-и-аудит)
8. [План реализации](#8-план-реализации)
9. [Тестирование](#9-тестирование)
10. [Риски и митигации](#10-риски-и-митигации)

---

## 1. Введение и обоснование

### 1.1 Проблема

Генеалогические платформы сталкиваются с фундаментальной проблемой **"ссылочной гнили" (link rot)**:

- Пользователи хранят фото и документы в личных облаках (Google Drive, Яндекс.Диск)
- Ссылки умирают при смене пароля, блокировке аккаунта или смерти владельца
- История семьи оказывается привязана к коммерческому решению корпорации
- При утрате доступа к файлу невозможно доказать факт существования архивного документа

### 1.2 Проблема наследования

Вторая критическая проблема — **деструктивные действия наследников**:

- Наследник получает полный доступ к архиву предков
- Может случайно или намеренно удалить карточки персон, фото, документы
- Может закрыть доступ другим подтвержденным родственникам
- История рода теряется безвозвратно

### 1.3 Решение

Предлагается реализовать **изолированный модуль Media Vault** с концепцией **Custodianship** (Хранительство):

1. **Принудительное копирование файлов** в наше S3-хранилище (отказ от внешних ссылок)
2. **Версионность и контроль целостности** (SHA-256)
3. **Роль CUSTODIAN** вместо OWNER для наследников
4. **Запрет на удаление унаследованных сущностей** без арбитража
5. **Цифровое завещание** с обязательным подтверждением наследников

---

## 2. Цели и ограничения

### 2.1 Цели

| Цель | Критерий успеха |
|------|-----------------|
| Сохранность данных | Гарантия доступности файлов в течение 100 лет |
| Защита от деструкции | Наследник не может удалить унаследованные файлы |
| Целостность | Автоматическое обнаружение подмены файлов |
| Масштабируемость | Поддержка 10 млн файлов без деградации |
| Соответствие GDPR/152-ФЗ | Право на забвение для владельца, но не для наследников |

### 2.2 Ограничения

- **До 10 файлов на одно событие** (LifeEvent)
- **Максимальный размер файла:** 20 МБ
- **Поддерживаемые форматы:**
  - Изображения: JPEG, PNG, WebP, HEIC
  - Документы: PDF
  - Аудио (будущее): MP3, WAV
- **Хранение:** только в нашем S3-хранилище (внешние ссылки запрещены)
- **Шифрование:** обязательное для всех файлов (SSE-SSEKMS)

---

## 3. Архитектура решения

### 3.1 Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS + JWT
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              API Gateway (FastAPI)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Persons API  │  │ Trees API    │  │ Media Vault  │      │
│  │              │  │              │  │ (изолирован) │      │
│  └──────────────┘  └──────────────┘  └──────┬───────┘      │
└──────────────────────────────────────────────┼──────────────┘
                                               │
              ┌────────────────────────────────┼────────────┐
              │                                │            │
              ▼                                ▼            ▼
    ┌─────────────────┐            ┌─────────────────┐  ┌─────────┐
    │  PostgreSQL     │            │  S3 Storage     │  │ Redis   │
    │  (метаданные)   │            │  (файлы)        │  │ (кэш)   │
    │                 │            │  - Версионность │  │         │
    │  - MediaFile    │            │  - Шифрование   │  └─────────┘
    │  - AccessLog    │            │  - SHA-256      │
    │  - Inheritance  │            │  - Cold Archive │
    └─────────────────┘            └─────────────────┘
```

### 3.2 Логическая изоляция модуля

Модуль Media Vault реализуется как **строго изолированный доменный контекст**:

```
app/
├── services/
│   └── media_vault/              # Изолированный модуль
│       ├── __init__.py
│       ├── models.py             # MediaFile, MediaAccessLog
│       ├── schemas.py            # Pydantic-схемы
│       ├── storage_service.py    # Работа с S3
│       ├── integrity_service.py  # SHA-256 проверки
│       ├── access_service.py     # Проверка прав доступа
│       └── inheritance_service.py # Логика наследования
├── api/
│   └── media.py                  # Эндпоинты Media Vault
└── core/
    └── custodianship.py          # Роли и правила Custodianship
```

**Преимущество:** При росте нагрузки эту папку можно за 1 день вынести в отдельный микросервис без переписывания бизнес-логики.

### 3.3 Жизненный цикл файла

```
1. Пользователь загружает файл
   ↓
2. Вычисляется SHA-256 хэш
   ↓
3. Файл шифруется и сохраняется в S3 (версия v1)
   ↓
4. Метаданные (путь, хэш, владелец) сохраняются в БД
   ↓
5. Создается запись в MediaAccessLog
   ↓
6. При скачивании: проверка хэша → отдача файла
   ↓
7. Ежегодная фоновая проверка целостности всех файлов
   ↓
8. Через 10 лет без обращений → перенос в Cold Archive
```

---

## 4. Модели данных

### 4.1 MediaFile (Метаданные файла)

```python
class MediaFile(Base):
    __tablename__ = "media_files"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('life_events.id'), nullable=False)
    
    # Информация о файле
    file_type = Column(String(20), nullable=False)  # "photo" | "document"
    mime_type = Column(String(100), nullable=False)  # "image/jpeg"
    original_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # в байтах
    
    # Хранение
    storage_path = Column(String(500), nullable=False)  # Путь в S3
    thumbnail_path = Column(String(500), nullable=True)  # Превью
    sha256_hash = Column(String(64), nullable=False)  # Контрольная сумма
    current_version = Column(Integer, default=1)
    
    # Наследование
    is_inherited = Column(Boolean, default=False)  # Защищен от удаления
    inherited_from_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    inheritance_date = Column(DateTime, nullable=True)
    
    # Аудит
    uploaded_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
```

### 4.2 MediaAccessLog (Аудит-лог)

```python
class MediaAccessLog(Base):
    __tablename__ = "media_access_logs"
    
    id = Column(Integer, primary_key=True)
    media_file_id = Column(Integer, ForeignKey('media_files.id'), nullable=False)
    
    action = Column(String(50), nullable=False)  # upload/download/delete/restore
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    details = Column(JSON, nullable=True)  # Дополнительные данные
    created_at = Column(DateTime, server_default=func.now())
```

### 4.3 InheritancePlan (Цифровое завещание)

```python
class InheritancePlan(Base):
    __tablename__ = "inheritance_plans"
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Список наследников (до 5 человек)
    heirs = Column(JSON, nullable=False)  # [{"user_id": 1, "confirmed": true}, ...]
    
    # Условия активации
    inactivity_months = Column(Integer, default=18)  # Месяцев без активности
    requires_death_certificate = Column(Boolean, default=False)
    
    # Статус
    status = Column(String(20), default="draft")  # draft/active/executed
    activated_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### 4.4 HardDeleteRequest (Запрос на удаление унаследованного)

```python
class HardDeleteRequest(Base):
    __tablename__ = "hard_delete_requests"
    
    id = Column(Integer, primary_key=True)
    media_file_id = Column(Integer, ForeignKey('media_files.id'), nullable=False)
    requested_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending/approved/rejected
    
    # Голосование родственников
    votes = Column(JSON, nullable=True)  # [{"user_id": 1, "vote": "approve"}, ...]
    required_approvals = Column(Integer, default=2)
    
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
```

---

## 5. API спецификация

### 5.1 Загрузка файла

**`POST /media/events/{event_id}/upload`**

Запрос (multipart/form-data):
```
file: <binary>
file_type: "photo" | "document"
description: "Свидетельство о рождении"
```

Ответ (201 Created):
```json
{
  "id": 42,
  "event_id": 15,
  "file_type": "document",
  "original_name": "birth_certificate.pdf",
  "file_size": 1234567,
  "sha256_hash": "a1b2c3d4...",
  "uploaded_by_id": 1,
  "created_at": "2026-09-19T14:30:00Z",
  "is_inherited": false
}
```

Ошибки:
- `400` — неверный тип файла или размер > 20 МБ
- `403` — нет прав на редактирование события
- `409` — превышен лимит 10 файлов на событие

### 5.2 Получение списка файлов события

**`GET /media/events/{event_id}/files`**

Ответ (200 OK):
```json
[
  {
    "id": 42,
    "file_type": "document",
    "original_name": "birth_certificate.pdf",
    "file_size": 1234567,
    "thumbnail_url": "/media/42/thumbnail",
    "download_url": "/media/42/download",
    "uploaded_by_id": 1,
    "is_inherited": false
  }
]
```

### 5.3 Скачивание файла

**`GET /media/files/{file_id}/download`**

Ответ:
- `200` — бинарный поток файла с заголовком `Content-Disposition: attachment`
- `403` — нет прав на просмотр
- `404` — файл не найден

### 5.4 Удаление файла

**`DELETE /media/files/{file_id}`**

Логика:
1. Если `is_inherited = false` → мягкое удаление (soft delete)
2. Если `is_inherited = true` → создание `HardDeleteRequest`

Ответ при soft delete (200 OK):
```json
{
  "status": "deleted",
  "message": "Файл удален"
}
```

Ответ при попытке удалить унаследованный файл (202 Accepted):
```json
{
  "status": "request_created",
  "request_id": 7,
  "message": "Создан запрос на удаление унаследованного файла. Требуется одобрение 2 родственников."
}
```

### 5.5 Назначение наследников

**`POST /users/{user_id}/inheritance-plan`**

Запрос:
```json
{
  "heirs": [
    {"user_id": 5, "email": "son@example.com"},
    {"user_id": 8, "email": "daughter@example.com"}
  ],
  "inactivity_months": 18,
  "requires_death_certificate": true
}
```

Ответ (201 Created):
```json
{
  "id": 1,
  "owner_id": 1,
  "heirs": [
    {"user_id": 5, "confirmed": true, "confirmed_at": "2026-09-19T15:00:00Z"},
    {"user_id": 8, "confirmed": false, "confirmation_sent_at": "2026-09-19T14:30:00Z"}
  ],
  "status": "active"
}
```

### 5.6 Голосование по запросу на удаление

**`POST /hard-delete-requests/{request_id}/vote`**

Запрос:
```json
{
  "vote": "approve",  // "approve" | "reject"
  "comment": "Файл действительно ошибочный"
}
```

---

## 6. Система наследования (Custodianship)

### 6.1 Роли пользователей

| Роль | Описание | Права |
|------|----------|-------|
| **OWNER** | Владелец дерева | Полный доступ, включая удаление |
| **CUSTODIAN** | Хранитель (наследник) | Добавление, редактирование, но **запрет на удаление унаследованного** |
| **CO_EDITOR** | Соавтор | Добавление и редактирование |
| **EDITOR** | Редактор | Редактирование существующего |
| **VIEWER** | Наблюдатель | Только просмотр |

### 6.2 Матрица прав доступа

| Операция | OWNER | CUSTODIAN | CO_EDITOR | EDITOR | VIEWER |
|----------|-------|-----------|-----------|--------|--------|
| Просмотр файлов | ✅ | ✅ | ✅ | ✅ | ✅ |
| Загрузка новых файлов | ✅ | ✅ | ✅ | ❌ | ❌ |
| Редактирование метаданных | ✅ | ✅ (не унаследованных) | ✅ (не унаследованных) | ❌ | ❌ |
| Удаление своих файлов | ✅ | ✅ | ❌ | ❌ | ❌ |
| Удаление унаследованных файлов | ✅ (только через арбитраж) | ❌ (только через арбитраж) | ❌ | ❌ | ❌ |
| Назначение наследников | ✅ | ❌ | ❌ | ❌ | ❌ |

### 6.3 Процесс активации наследования

```
1. Владелец создает InheritancePlan
   ↓
2. Система отправляет email потенциальным наследникам
   ↓
3. Наследники подтверждают согласие (клик по ссылке + вход в систему)
   ↓
4. Plan получает статус "active"
   ↓
5. При триггере (смерть владельца / неактивность 18 мес):
   ↓
6. Все файлы владельца получают is_inherited = true
   ↓
7. Наследники получают роль CUSTODIAN
   ↓
8. Уведомление всем подтвержденным родственникам о смене статуса
```

### 6.4 Триггеры активации

1. **Ручная передача:** Владелец нажимает "Передать архив наследникам"
2. **Автоматическая по неактивности:**
   - Владелец не заходил 18 месяцев
   - Наследник инициирует проверку
   - Система отправляет запрос владельцу (email + SMS)
   - Если нет ответа 30 дней → передача прав
3. **По факту смерти:**
   - Наследник загружает свидетельство о смерти
   - Модератор проверяет документ
   - Передача прав

---

## 7. Безопасность и аудит

### 7.1 Шифрование

- **At rest:** AES-256 через SSE-SSEKMS (ключи в KMS)
- **In transit:** TLS 1.3 обязательно
- **Ключи:** каждый файл шифруется уникальным data key, который сам зашифрован master key

### 7.2 Контроль целостности

```python
async def verify_file_integrity(file_id: int) -> bool:
    """
    Проверяет целостность файла по SHA-256 хэшу.
    Запускается:
    - При каждом скачивании
    - Ежегодно для всех файлов (фоновая задача)
    """
    file = await db.get(MediaFile, file_id)
    actual_hash = await compute_sha256_from_s3(file.storage_path)
    
    if actual_hash != file.sha256_hash:
        # КРИТИЧЕСКОЕ СОБЫТИЕ
        await log_security_alert(
            event_type="INTEGRITY_VIOLATION",
            file_id=file_id,
            expected_hash=file.sha256_hash,
            actual_hash=actual_hash
        )
        # Автоматическое восстановление из предыдущей версии
        await restore_from_previous_version(file)
        return False
    
    return True
```

### 7.3 Аудит-лог

**Все операции логируются:**
- Загрузка файла
- Скачивание файла
- Попытка удаления (успешная и неуспешная)
- Изменение прав доступа
- Активация наследования
- Голосование по HardDeleteRequest

**Формат записи:**
```json
{
  "timestamp": "2026-09-19T14:30:00Z",
  "user_id": 1,
  "action": "DELETE_ATTEMPT",
  "resource_type": "MediaFile",
  "resource_id": 42,
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "result": "BLOCKED",
  "reason": "File is inherited, requires arbitration",
  "details": {
    "is_inherited": true,
    "request_id": 7
  }
}
```

### 7.4 Защита от атак

| Атака | Митигация |
|-------|-----------|
| Подмена файла в S3 | SHA-256 проверка + версионность |
| Удаление через SQL-инъекцию | Soft delete + версионность S3 |
| Массовая загрузка (DoS) | Rate limiting: 100 файлов/час на пользователя |
| XSS через метаданные | Санитизация всех строковых полей |
| Несанкционированный доступ | JWT + проверка прав на уровне сервиса |
| Удаление унаследованного | Блокировка на уровне БД (CHECK constraint) |

---

## 8. План реализации

### Этап 1: Базовая загрузка/скачивание (2 недели)

- [ ] Модели `MediaFile`, `MediaAccessLog`
- [ ] Интеграция с S3 (Yandex Object Storage)
- [ ] API: upload, download, list
- [ ] Валидация типов и размеров
- [ ] Тесты

### Этап 2: Целостность и версионность (1 неделя)

- [ ] Вычисление SHA-256 при загрузке
- [ ] Проверка при скачивании
- [ ] Включение версионности в S3
- [ ] Фоновая задача ежегодной проверки
- [ ] Тесты целостности

### Этап 3: Система наследования (2 недели)

- [ ] Модель `InheritancePlan`
- [ ] API назначения наследников
- [ ] Email-подтверждение наследников
- [ ] Триггеры активации
- [ ] Роль CUSTODIAN и ограничения прав
- [ ] Тесты наследования

### Этап 4: Hard Delete Request (1 неделя)

- [ ] Модель `HardDeleteRequest`
- [ ] API голосования
- [ ] Логика кворума 2/3
- [ ] Интеграция с модерацией
- [ ] Тесты арбитража

### Этап 5: Холодное хранение (1 неделя)

- [ ] Фоновая задача анализа активности
- [ ] Перенос файлов старше 10 лет в Glacier
- [ ] API для восстановления из холодного архива
- [ ] Тесты

**Общая оценка:** 7 недель разработки

---

## 9. Тестирование

### 9.1 Юнит-тесты

```python
# test_integrity.py
async def test_sha256_verification():
    """Проверяет, что SHA-256 хэш вычисляется корректно."""
    
# test_access_control.py
async def test_custodian_cannot_delete_inherited_file():
    """Хранитель не может удалить унаследованный файл напрямую."""
    
async def test_custodian_can_upload_new_file():
    """Хранитель может загружать новые файлы."""

# test_inheritance.py
async def test_inheritance_activation():
    """Проверяет корректную активацию наследования."""
```

### 9.2 Интеграционные тесты

```python
async def test_full_inheritance_flow():
    """
    Полный сценарий:
    1. Пользователь загружает 5 файлов
    2. Назначает наследника
    3. Наследник подтверждает
    4. Имитируем смерть владельца
    5. Проверяем, что файлы помечены как is_inherited
    6. Пытаемся удалить файл как наследник → получаем HardDeleteRequest
    7. Второй родственник голосует "approve"
    8. Файл удален
    """
```

### 9.3 Тесты безопасности

```python
async def test_sql_injection_in_filename():
    """Проверяет защиту от SQL-инъекций через имя файла."""
    
async def test_xss_in_description():
    """Проверяет санитизацию описания файла."""
    
async def test_rate_limiting_on_upload():
    """Проверяет rate limiting при массовой загрузке."""
```

### 9.4 Нагрузочные тесты

- Загрузка 1000 файлов параллельно
- Скачивание 10000 файлов в минуту
- Проверка целостности 1 млн файлов

---

## 10. Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Потеря S3-хранилища | Низкая | Критическое | Георепликация + холодный архив |
| Утечка ключей шифрования | Средняя | Критическое | HSM + ротация ключей |
| Массовое удаление унаследованного | Средняя | Высокое | Арбитраж + аудит-лог |
| Отказ ответственных наследников | Средняя | Среднее | Резервные наследники |
| Юридические требования GDPR | Высокая | Среднее | Право на забвение для владельца, но не для наследников |
| Рост стоимости хранения | Высокая | Среднее | Автоматический переход в Cold Archive |

---

## 📎 Приложения

### Приложение А: Диаграмма последовательности загрузки файла

```
User          Frontend        API           MediaVault      S3          DB
 |               |             |               |            |           |
 |--upload------>|             |               |            |           |
 |               |--POST------>|               |            |           |
 |               |             |--validate---->|            |           |
 |               |             |               |--compute-->|           |
 |               |             |               |  SHA-256   |           |
 |               |             |               |--encrypt-->|           |
 |               |             |               |            |--save---->|
 |               |             |               |            |           |--save meta
 |               |             |<--------------|            |           |
 |               |<------------|               |            |           |
 |<--------------|             |               |            |           |
```

### Приложение Б: Пример конфигурации S3

```yaml
# S3 bucket configuration
bucket:
  name: istok-media-vault
  region: ru-central1
  versioning: true
  encryption:
    type: SSE-KMS
    kms_key_id: alias/istok-media-key
  
  lifecycle:
    rules:
      - id: cold-archive
        filter:
          prefix: ""
        transitions:
          - days: 3650  # 10 лет
            storage_class: COLD_STORAGE
        status: Enabled
  
  logging:
    target_bucket: istok-access-logs
    target_prefix: media-vault/
```

---

## 📝 История изменений

| Версия | Дата | Автор | Изменения |
|--------|------|-------|-----------|
| 1.0 | 2026-09-19 | Команда Исток | Первоначальная версия |

---

**Конец документа**