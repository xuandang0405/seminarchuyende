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

# CORS middleware
cors_origins = [o for o in settings.CORS_ORIGINS if o != "*"]
if not cors_origins:
    cors_origins = [
        "http://localhost:3000", "http://localhost:5173", "http://localhost:8000",
        "http://127.0.0.1:3000", "http://127.0.0.1:5173", "http://127.0.0.1:8000"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
