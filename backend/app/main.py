import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB via PyMongo Async
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Hệ thống Thuyết minh Du lịch Tự động Đa ngôn ngữ Quận 4 (FastAPI + PyMongo Async + MongoDB).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Proxy Headers Middleware for Reverse Proxy (Nginx)
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts=settings.TRUSTED_HOSTS if isinstance(settings.TRUSTED_HOSTS, list) else "*"
)

# CORS middleware with explicit origins & credentials support
allowed = settings.CORS_ALLOWED_ORIGINS or settings.CORS_ORIGINS or []
cors_origins = [o.strip().rstrip("/") for o in allowed if o != "*"]

# Automatically add PUBLIC_WEB_URL origin to allowed origins
if settings.PUBLIC_WEB_URL:
    pub_origin = settings.PUBLIC_WEB_URL.strip().rstrip("/")
    if pub_origin and pub_origin not in cors_origins:
        cors_origins.append(pub_origin)

if not cors_origins:
    cors_origins = [
        "http://localhost:3000", "http://localhost:5173", "http://localhost:8000",
        "http://127.0.0.1:3000", "http://127.0.0.1:5173", "http://127.0.0.1:8000"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|1\.55\.58\.251)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "Idempotency-Key",
        "Accept",
        "Origin",
        "User-Agent",
    ],
    expose_headers=["ETag", "X-Request-ID"],
)

# Prevent stale browser caching of frontend static assets during updates
@app.middleware("http")
async def add_frontend_cache_control_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith(("/admin", "/client")):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response

# Mount Static Media Storage
if os.path.exists(settings.MEDIA_STORAGE_DIR):
    app.mount("/storage", StaticFiles(directory=settings.MEDIA_STORAGE_DIR), name="storage")

# Mount Frontend Client & Admin (legacy fallback if present)
frontend_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
client_dir = os.path.join(frontend_base, "client")
admin_dir = os.path.join(frontend_base, "admin")

if os.path.exists(client_dir):
    app.mount("/client", StaticFiles(directory=client_dir, html=True), name="client")

if os.path.exists(admin_dir):
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")

# Include API Router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}!",
        "version": "1.0.0",
        "documentation": "/docs",
        "tourist_client": "/client/",
        "admin_portal": "/admin/",
        "health_check": "/api/v1/health"
    }
