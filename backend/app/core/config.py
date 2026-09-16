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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access token (15 mins)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30    # Long-lived refresh token in HttpOnly cookie

    # Cookies & CSRF Settings
    SESSION_COOKIE_NAME: str = "tourvoice_refresh_token"
    CSRF_COOKIE_NAME: str = "tourvoice_csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    FRONTEND_URL: str = "http://localhost:5173"
    FRONTEND_CALLBACK_URL: str = "http://localhost:5173/auth/callback"
    ALLOWED_RETURN_PATHS: List[str] = [
        "/", "/dashboard", "/pois", "/account", "/account/security", "/owner-registration", "/menu", "/analytics"
    ]

    # Google OAuth 2.0 / OIDC Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

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
