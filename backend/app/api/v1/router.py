from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    languages,
    pois,
    poi_contents,
    audio,
    tours,
    packages,
    qr,
    jobs,
    owner,
    admin,
    ai,
    analytics,
    sessions,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(languages.router)
api_router.include_router(pois.router)
api_router.include_router(poi_contents.router)
api_router.include_router(audio.router)
api_router.include_router(tours.router)
api_router.include_router(packages.router)
api_router.include_router(qr.router)
api_router.include_router(jobs.router)
api_router.include_router(owner.router)
api_router.include_router(admin.router)
api_router.include_router(ai.router)
api_router.include_router(analytics.router)
api_router.include_router(sessions.router)
