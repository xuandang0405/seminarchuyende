import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api.v1.router import api_router
from app.services.job_worker import job_worker

worker_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB Atlas
    await connect_to_mongo()
    # Start async content job worker
    global worker_task
    worker_task = asyncio.create_task(job_worker.worker_loop())
    yield
    # Shutdown
    if worker_task:
        worker_task.cancel()
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TourVoice: Hệ Thống Thuyết Minh Du Lịch Đa Ngôn Ngữ Quận 4 (FastAPI + MongoDB Atlas).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Media Storage
if os.path.exists(settings.MEDIA_STORAGE_DIR):
    app.mount("/storage", StaticFiles(directory=settings.MEDIA_STORAGE_DIR), name="storage")

# Mount Frontend Client & Admin (relative to backend dir)
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
