import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "PICTOART - Doctor Pencil Sketch Certificate Generator"
    ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default="super-secret-key-change-in-production-1234567890")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./pictoart.db")
    
    # Storage
    STORAGE_DIR: str = Field(default="./storage")
    USE_S3_STORAGE: bool = Field(default=False)
    S3_ENDPOINT_URL: str = Field(default="")
    S3_ACCESS_KEY_ID: str = Field(default="")
    S3_SECRET_ACCESS_KEY: str = Field(default="")
    S3_BUCKET_NAME: str = Field(default="pictoart-certificates")
    
    # Worker & Redis Queue
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    WORKER_MODE: str = Field(default="threaded") # 'threaded' (async background thread) or 'rq' (Redis Queue)
    
    # App Settings
    BASE_URL: str = Field(default="http://localhost:8000")
    MAX_UPLOAD_SIZE_MB: int = Field(default=10)
    MIN_IMAGE_RESOLUTION: tuple[int, int] = (400, 400)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure storage directories exist
os.makedirs(os.path.join(settings.STORAGE_DIR, "originals"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "generated"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "exports"), exist_ok=True)
