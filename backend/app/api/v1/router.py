from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, languages, pois, tours

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(languages.router)
api_router.include_router(pois.router)
api_router.include_router(tours.router)
