from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "TourVoice API"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # MongoDB Settings
    MONGODB_URL: Optional[str] = None
    MONGODB_URI: Optional[str] = None
    MONGODB_USERNAME: Optional[str] = None
    MONGODB_PASSWORD: Optional[str] = None
    DATABASE_NAME: str = "tour_guide"

    @property
    def mongodb_connection_string(self) -> str:
        uri = self.MONGODB_URI or self.MONGODB_URL
        if uri:
            return uri
        return "mongodb://localhost:27017"

    # Security Settings
    SECRET_KEY: str = "tourvoice_super_secret_jwt_key_seminar_district_4"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Media Storage
    MEDIA_STORAGE_DIR: str = "storage"

    # Default Super Admin
    SUPERADMIN_EMAIL: str = "admin@tourvoice.vn"
    SUPERADMIN_PASSWORD: str = "Admin@123456"

    # External AI / TTS / Weather integrations (Optional)
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "*"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure media storage directories exist
os.makedirs(os.path.join(settings.MEDIA_STORAGE_DIR, "audio"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_STORAGE_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_STORAGE_DIR, "packages"), exist_ok=True)
