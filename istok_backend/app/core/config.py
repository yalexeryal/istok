from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://istok_user:istok_password@localhost:5433/istok_db"
    SECRET_KEY: str = "your_super_secret_key_for_development_123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    model_config = ConfigDict(env_file=".env")

settings = Settings()