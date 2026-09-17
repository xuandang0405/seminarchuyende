"""Router for Tour Access Decisions & Playback Grants.

Section 5 & 10 of prompt.
BR-ACCESS-01 / BR-TRIAL-01..05.
"""

from typing import Any, Dict, Optional, Tuple
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
import jwt

from app.core.config import settings
from app.repositories.auth_repo import auth_repo
from app.services.guest_service import guest_service
from app.services.access_service import access_service
from app.schemas.access import TourAccessResponse, PlaybackGrantRequest, PlaybackGrantResponse

router = APIRouter(tags=["Tour Access & Playback Grants"])


async def resolve_subject(request: Request) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Resolves whether request is from an authenticated user or a guest session."""
    user = None
    guest = None

    # 1. Try Bearer token
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                u = await auth_repo.get_user_by_id(user_id)
                if u and u.get("is_active", True):
                    user = u
        except Exception:
            pass

    # 2. If not a user, check guest credential
    if not user:
        cred = (
            request.headers.get("X-Guest-Credential")
            or request.headers.get("x-guest-credential")
            or request.headers.get("X-Guest-Token")
            or request.headers.get("x-guest-token")
            or request.cookies.get("guest_session_credential")
        )
        if cred and isinstance(cred, str) and cred.strip():
            g = await guest_service.resolve_guest_session(cred.strip())
            if g:
                guest = g

    return user, guest


@router.get("/tours/{tour_id}/access", response_model=TourAccessResponse)
async def get_tour_access_endpoint(
    tour_id: str,
    request: Request
):
    """Section 5: Returns unified access permissions for the current subject on this tour."""
    user, guest = await resolve_subject(request)
    return await access_service.get_tour_access(tour_id=tour_id, user=user, guest=guest)


@router.post("/playback-grants", response_model=PlaybackGrantResponse)
async def request_playback_grant_endpoint(
    req: PlaybackGrantRequest,
    request: Request
):
    """Section 5: Authorizes and issues a short-lived playback grant token for narration streaming."""
    user, guest = await resolve_subject(request)
    if not user and not guest:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cần phiên đăng nhập hoặc phiên khách để yêu cầu phát thuyết minh."
        )

    res = await access_service.request_playback_grant(
        tour_id=req.tour_id,
        poi_id=req.poi_id,
        lang=req.lang,
        trigger_source=req.trigger_source,
        consent_trial=req.consent_trial,
        idempotency_key=req.idempotency_key,
        user=user,
        guest=guest
    )

    if not res.get("success"):
        err_code = res.get("error", "ACCESS_DENIED")
        status_code = status.HTTP_403_FORBIDDEN
        if err_code == "TOUR_NOT_FOUND" or err_code == "POI_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND
        elif err_code == "TRIAL_CONSENT_REQUIRED":
            status_code = status.HTTP_403_FORBIDDEN

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": err_code,
                "error_code": err_code,
                "message": res.get("message", "Từ chối truy cập.")
            }
        )

    res["granted"] = True
    return res
