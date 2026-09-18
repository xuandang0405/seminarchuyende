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

    # Environment and Domain Settings
    APP_ENV: str = "production"  # "development" | "staging" | "production"
    PUBLIC_WEB_URL: str = "http://localhost:8000"
    TRUSTED_HOSTS: Union[List[str], str] = ["*"]
    FORWARDED_ALLOW_IPS: str = "*"

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

    # Payment & Trial Policy Configuration
    PAYMENT_MODE: str = "mock"  # "mock" | "live"
    TRIAL_POLICY_VERSION: int = 1
    OFFLINE_LICENSE_VALID_DAYS: int = 7

    # VNPAY Configuration
    VNPAY_TMN_CODE: str = "DEMO"
    VNPAY_HASH_SECRET: str = "DEMOHASHSECRET1234567890ABCDEF"
    VNPAY_PAY_URL: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    VNPAY_RETURN_URL: str = "http://localhost:8000/client/index.html"

    # payOS Configuration
    PAYOS_CLIENT_ID: Optional[str] = "demo-client-id"
    PAYOS_API_KEY: Optional[str] = "demo-api-key"
    PAYOS_CHECKSUM_KEY: Optional[str] = "demo-checksum-key-1234567890"
    # Map and Geo Configuration (District 4, HCMC)
    MAP_DEFAULT_CENTER_LAT: float = 10.7635
    MAP_DEFAULT_CENTER_LNG: float = 106.7042
    MAP_DEFAULT_ZOOM: int = 15
    MAP_BOUNDS_MIN_LNG: float = 106.685
    MAP_BOUNDS_MIN_LAT: float = 10.745
    MAP_BOUNDS_MAX_LNG: float = 106.720
    MAP_BOUNDS_MAX_LAT: float = 10.775
    MAP_TILE_PROVIDER_NAME: str = "CartoDB Voyager"
    MAP_TILE_STYLE_URL: str = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
    MAP_ATTRIBUTION: str = "© CartoDB Voyager | OpenStreetMap contributors"

    # Routing Engine Configuration (OSRM)
    ROUTING_PROVIDER_URL: str = "https://router.project-osrm.org"
    ROUTING_TIMEOUT_SECONDS: float = 6.0
    ROUTING_CACHE_TTL_HOURS: int = 24
    ROUTING_MAX_POINTS_PER_REQUEST: int = 25

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
    CORS_ALLOWED_ORIGINS: Optional[Union[List[str], str]] = None

    @field_validator("CORS_ORIGINS", "CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str], None]) -> Union[List[str], None]:
        if v is None:
            return None
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
