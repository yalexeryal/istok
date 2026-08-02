from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=6,
        max_length=72,  # Ограничение bcrypt
        description="Пароль от 6 до 72 символов"
    )
    full_name: str = Field(min_length=1, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "ivan@example.com",
                "password": "securepassword123",
                "full_name": "Иван Иванов"
            }
        }

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    created_at: datetime

    class Config:
        from_attributes = True