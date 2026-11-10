import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.db.indexes import create_all_indexes
from app.api.v1.router import api_router
import logging

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime()
    # Startup: Connect to MongoDB via PyMongo Async
    await connect_to_mongo()
    db = get_database()
    if db is not None:
        try:
            await create_all_indexes(db)
            from app.db.bootstrap import bootstrap
            await bootstrap(db)
            logger.info("Successfully ensured all 22 MongoDB collection indexes.")
        except Exception:
            await close_mongo_connection()
            raise
    local_worker = None
    if settings.APP_ENV == "development" and os.getenv("TOURVOICE_LOCAL_WORKER") == "1":
        from app.services.localization_worker import run_job_loop
        local_worker = asyncio.create_task(run_job_loop())
    try:
        yield
    finally:
        if local_worker:
            local_worker.cancel()
            await asyncio.gather(local_worker, return_exceptions=True)
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
    trusted_hosts=settings.FORWARDED_ALLOW_IPS.split(",")
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
        "If-None-Match",
        "X-CSRF-Token",
        "Idempotency-Key",
        "Accept",
        "Accept-Language",
        "Origin",
        "User-Agent",
        "X-Device-Token", "X-Guest-Credential", "X-Guest-Token", "X-Idempotency-Key",
    ],
    expose_headers=["ETag", "X-Request-ID", "Content-Language"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    import uuid
    from urllib.parse import urlsplit
    from app.core.security import verify_csrf_token
    if request.method not in ("GET", "HEAD", "OPTIONS") and not request.headers.get("Authorization"):
        ambient = request.cookies.get(settings.SESSION_COOKIE_NAME) or request.cookies.get("tourvoice_access_token")
        if ambient:
            origin = request.headers.get("Origin")
            expected = {str(request.base_url).rstrip("/"), settings.PUBLIC_WEB_URL.rstrip("/"), settings.FRONTEND_URL.rstrip("/")}
            csrf_ok = verify_csrf_token(request.cookies.get(settings.CSRF_COOKIE_NAME), request.headers.get(settings.CSRF_HEADER_NAME))
            if origin not in expected and not csrf_ok:
                return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)
    request_id = uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if settings.COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

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
image_dir = os.path.join(settings.MEDIA_STORAGE_DIR, "images")
if os.path.exists(image_dir):
    app.mount("/storage/images", StaticFiles(directory=image_dir), name="images")

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


class MapPackFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code in (200, 206, 304):
            response.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable" if path.endswith(".pmtiles") else "no-cache"
            )
        return response

SPA_ROUTES = [
    "/admin", "/web-admin", "/client", "/pois", "/tours", "/qr-codes",
    "/orders", "/analytics", "/login", "/auth", "/account", "/tourist",
    "/forgot-password", "/reset-password", "/dashboard", "/owner",
    "/moderation", "/audit-logs", "/403"
]
if os.path.exists(react_admin_dist) and os.path.exists(os.path.join(react_admin_dist, "index.html")):
    for r in SPA_ROUTES:
        app.mount(r, SPAStaticFiles(directory=react_admin_dist, html=True), name=r.strip("/"))
    assets_dir = os.path.join(react_admin_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="react-assets")
        app.mount("/admin/assets", StaticFiles(directory=assets_dir), name="react-admin-assets")
    maps_dir = os.path.join(react_admin_dist, "static", "maps")
    if os.path.isdir(maps_dir):
        app.mount("/static/maps", MapPackFiles(directory=maps_dir), name="public-map-packs")

    def public_build_file(filename):
        async def serve():
            return FileResponse(os.path.join(react_admin_dist, filename),
                headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})
        return serve
    for filename in ("index.html", "sw.js", "registerSW.js", "manifest.webmanifest", "logo-vuong.png", "logo-ngang.png"):
        if os.path.isfile(os.path.join(react_admin_dist, filename)):
            app.add_api_route("/" + filename, public_build_file(filename), methods=["GET"], include_in_schema=False)

@app.get("/storage/audio/{storage_key:path}", include_in_schema=False)
async def protected_legacy_audio(storage_key: str, request: Request, grant_token: str = None):
    from app.api.v1.endpoints.audio import stream_audio_endpoint
    return await stream_audio_endpoint("audio/" + storage_key, request, grant_token)

# Include API Router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and not request.url.path.startswith("/api"):
        index_file = os.path.join(react_admin_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file, media_type="text/html")
        return RedirectResponse(url="/client/", status_code=302)
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}!",
        "version": "1.0.0",
        "documentation": "/docs",
        "admin_react": "/admin/",
        "client_react": "/client/",
        "health_check": "/api/v1/health"
    }
