import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://taskmaster:taskmaster@localhost:5433/taskmaster")
    jwt_secret: str = os.getenv(
        "JWT_SECRET", "change-this-development-secret-32-bytes-minimum"
    )
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
    attachment_dir: str = os.getenv("ATTACHMENT_DIR", "storage/attachments")

settings = Settings()
