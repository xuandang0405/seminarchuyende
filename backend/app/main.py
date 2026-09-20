import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.db.indexes import create_all_indexes
from app.api.v1.router import api_router
import logging

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB via PyMongo Async
    await connect_to_mongo()
    db = get_database()
    if db is not None:
        try:
            await create_all_indexes(db)
            logger.info("Successfully ensured all 22 MongoDB collection indexes.")
        except Exception as e:
            logger.warning(f"Could not initialize all MongoDB indexes automatically: {e}")
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(exc)}", "type": exc.__class__.__name__}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Đã xảy ra lỗi máy chủ nội bộ. Vui lòng thử lại sau hoặc liên hệ quản trị viên."}
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
        "http://127.0.0.1:3000", "http://127.0.0.1:5173", "http://127.0.0.1:8000",
        "http://1.55.58.251:8000"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "Idempotency-Key",
        "Accept",
        "Accept-Language",
        "Origin",
        "User-Agent",
    ],
    expose_headers=["ETag", "X-Request-ID", "Content-Language"],
)

# Internationalization & Localization Middleware (RFC 9110)
from app.core.i18n import LanguageMiddleware
app.add_middleware(LanguageMiddleware)

# Prevent stale browser caching of admin static assets during updates

@app.middleware("http")
async def add_frontend_cache_control_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response

# Mount Static Media Storage
if os.path.exists(settings.MEDIA_STORAGE_DIR):
    app.mount("/storage", StaticFiles(directory=settings.MEDIA_STORAGE_DIR), name="storage")

# Mount React Web-Admin (Primary CMS)
react_admin_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "web-admin", "dist"))

class SPAStaticFiles(StaticFiles):
    """Serves SPA static files with fallback to index.html for React Router paths."""
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code == 404 and "." not in path.split("/")[-1]:
                return await super().get_response("index.html", scope)
            return response
        except Exception:
            if "." not in path.split("/")[-1]:
                return await super().get_response("index.html", scope)
            raise

SPA_ROUTES = [
    "/admin", "/web-admin", "/client", "/pois", "/tours", "/qr-codes",
    "/orders", "/analytics", "/login", "/auth", "/account", "/tourist",
    "/forgot-password", "/reset-password", "/dashboard", "/owner"
]
if os.path.exists(react_admin_dist) and os.path.exists(os.path.join(react_admin_dist, "index.html")):
    for r in SPA_ROUTES:
        app.mount(r, SPAStaticFiles(directory=react_admin_dist, html=True), name=r.strip("/"))
    assets_dir = os.path.join(react_admin_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="react-assets")

# Include API Router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and not request.url.path.startswith("/api"):
        return RedirectResponse(url="/admin/", status_code=302)
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}!",
        "version": "1.0.0",
        "documentation": "/docs",
        "admin_react": "/admin/",
        "client_react": "/client/",
        "mobile_app": "React Native Expo (cd mobile && npm start)",
        "health_check": "/api/v1/health"
    }
