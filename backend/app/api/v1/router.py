from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    pois,
    menu,
    audio,
    tours,
    qr,
    owner,
    admin,
    analytics,
    packages,
    payments,
    guest_sessions,
    access,
    orders,
    me,
    map,
    routes,
    jobs,
    device,
    visitor_sessions,
    tour_sessions,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(map.router)
api_router.include_router(routes.router)
api_router.include_router(auth.router)
api_router.include_router(auth.router, prefix="/admin")
api_router.include_router(guest_sessions.router)
api_router.include_router(access.router)
api_router.include_router(orders.router)
api_router.include_router(me.router)
api_router.include_router(pois.router)
api_router.include_router(menu.router)
api_router.include_router(audio.router)
api_router.include_router(tours.router)
api_router.include_router(qr.router)
api_router.include_router(owner.router)
api_router.include_router(admin.router)
api_router.include_router(analytics.router)
api_router.include_router(packages.router)
api_router.include_router(payments.router)
api_router.include_router(jobs.router)
api_router.include_router(device.router)
api_router.include_router(visitor_sessions.router)
api_router.include_router(tour_sessions.router)


from typing import Any, Dict
import uuid

@api_router.post("/sessions")
async def create_tourist_session(req: Dict[str, Any] = None):
    """Creates a tourist telemetry session for client app."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    return {"status": "ok", "session_id": session_id, "_id": session_id}

