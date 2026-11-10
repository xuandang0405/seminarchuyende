from typing import List, Union, Optional
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "TourVoice API"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # MongoDB Settings
    MONGODB_URL: Optional[str] = None
    MONGODB_URI: Optional[str] = None
    MONGODB_ATLAS_URI: Optional[str] = None
    MONGODB_USERNAME: Optional[str] = None
    MONGODB_PASSWORD: Optional[str] = None
    DATABASE_NAME: str = Field("tour_guide", validation_alias=AliasChoices("DATABASE_NAME", "MONGODB_DB_NAME"))

    @property
    def mongodb_connection_string(self) -> str:
        uri = self.MONGODB_URI or self.MONGODB_URL
        if uri:
            return uri
        return "mongodb://localhost:27017"

    # Security Settings
    SECRET_KEY: str = Field("", validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET"))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access token (15 mins)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30    # Long-lived refresh token in HttpOnly cookie

    # Environment and Domain Settings
    APP_ENV: str = "production"  # "development" | "staging" | "production"
    PUBLIC_WEB_URL: str = "https://seminar.bkpvp.top"
    TRUSTED_HOSTS: Union[List[str], str] = ["*"]
    FORWARDED_ALLOW_IPS: str = "127.0.0.1"

    # Cookies & CSRF Settings
    SESSION_COOKIE_NAME: str = "tourvoice_refresh_token"
    CSRF_COOKIE_NAME: str = "tourvoice_csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    FRONTEND_URL: str = "https://seminar.bkpvp.top"
    FRONTEND_CALLBACK_URL: str = "https://seminar.bkpvp.top/auth/callback"
    ALLOWED_RETURN_PATHS: List[str] = [
        "/", "/client", "/tourist", "/dashboard", "/pois", "/tours", "/qr-codes",
        "/orders", "/account", "/account/security", "/owner-registration", "/menu",
        "/analytics", "/admin/login", "/client/login", "/login"
    ]

    # Google OAuth 2.0 / OIDC Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "https://seminar.bkpvp.top/api/v1/auth/google/callback"

    # Media Storage
    MEDIA_STORAGE_DIR: str = "storage"
    ALLOW_MOCK_DATABASE: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@tourvoice.vn"
    SMTP_STARTTLS: bool = True
    BANK_BIN: Optional[str] = None
    BANK_ACCOUNT_NO: Optional[str] = None
    BANK_ACCOUNT_NAME: Optional[str] = None

    # Default Super Admin
    SUPERADMIN_EMAIL: str = "admin@tourvoice.vn"
    SUPERADMIN_PASSWORD: str = "Admin@123456"
    SUPERADMIN_BOOTSTRAP_MODE: str = "disabled"

    # External AI / TTS / Weather integrations (Optional)
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Payment & Trial Policy Configuration
    PAYMENT_MODE: str = "mock"  # "mock" | "live"
    TRIAL_POLICY_VERSION: int = 1
    OFFLINE_LICENSE_VALID_DAYS: int = 7
    OFFLINE_LICENSE_PRIVATE_KEY: Optional[str] = None

    # VNPAY Configuration
    VNPAY_TMN_CODE: str = "DEMO"
    VNPAY_HASH_SECRET: str = "DEMOHASHSECRET1234567890ABCDEF"
    VNPAY_PAY_URL: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    VNPAY_API_URL: str = "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction"
    VNPAY_IP_ADDRESS: str = "127.0.0.1"
    VNPAY_RETURN_URL: str = "http://localhost:8000/admin/orders"

    # payOS Configuration
    PAYOS_CLIENT_ID: Optional[str] = None
    PAYOS_API_KEY: Optional[str] = None
    PAYOS_CHECKSUM_KEY: Optional[str] = None
    PAYOS_ENDPOINT: str = "https://api-merchant.payos.vn"
    # Map and Geo Configuration (District 4, HCMC)
    MAP_DEFAULT_CENTER_LAT: float = 10.7635
    MAP_DEFAULT_CENTER_LNG: float = 106.7042
    MAP_DEFAULT_ZOOM: int = 15
    MAP_BOUNDS_MIN_LNG: float = 106.685
    MAP_BOUNDS_MIN_LAT: float = 10.745
    MAP_BOUNDS_MAX_LNG: float = 106.720
    MAP_BOUNDS_MAX_LAT: float = 10.775
    MAP_TILE_PROVIDER_NAME: str = "Google Maps"
    MAP_TILE_STYLE_URL: str = "https://mt{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
    MAP_ATTRIBUTION: str = "© Google Maps"

    # Routing Engine Configuration (OSRM)
    ROUTING_PROVIDER_URL: str = "https://routing.openstreetmap.de/routed-{mode}"
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
        "http://seminar.bkpvp.top",
        "https://seminar.bkpvp.top",
        "http://serminar.bkpvp.top",
        "https://serminar.bkpvp.top",
        "*"
    ]
    CORS_ALLOWED_ORIGINS: Optional[Union[List[str], str]] = None

    @property
    def is_development(self) -> bool:
        return self.APP_ENV in ("development", "test", "testing")

    def validate_runtime(self):
        if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.startswith(("change", "CHANGE", "tourvoice_super")):
            raise RuntimeError("SECRET_KEY must be a unique random secret of at least 32 characters.")
        if not self.is_development:
            if self.DEBUG or self.ALLOW_MOCK_DATABASE or self.PAYMENT_MODE == "mock":
                raise RuntimeError("Production forbids DEBUG, mock database and mock payments.")
            if not self.PUBLIC_WEB_URL.startswith("https://") or not self.COOKIE_SECURE:
                raise RuntimeError("Production requires HTTPS and COOKIE_SECURE=true.")
            import base64
            try:
                if len(base64.b64decode(self.OFFLINE_LICENSE_PRIVATE_KEY or "", validate=True)) != 32:
                    raise ValueError()
            except Exception as exc:
                raise RuntimeError("OFFLINE_LICENSE_PRIVATE_KEY must be a base64-encoded 32-byte Ed25519 private seed.") from exc
            if not self.SMTP_HOST or not self.SMTP_FROM:
                raise RuntimeError("Production password recovery requires SMTP_HOST and SMTP_FROM.")

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
        env_file=(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
            "backend/.env",
            ".env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure media storage directories exist
os.makedirs(os.path.join(settings.MEDIA_STORAGE_DIR, "audio"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_STORAGE_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_STORAGE_DIR, "packages"), exist_ok=True)
