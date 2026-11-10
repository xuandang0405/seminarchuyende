"""Router for Tour Access Decisions & Playback Grants.

Section 5 & 10 of prompt.
BR-ACCESS-01 / BR-TRIAL-01..05.
"""

from typing import Any, Dict, Optional, Tuple
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from app.api.v1.endpoints.auth import get_optional_current_user
from app.services.guest_service import guest_service
from app.services.access_service import access_service
from app.services.session_service import session_service
from app.schemas.access import TourAccessResponse, PlaybackGrantRequest, PlaybackGrantResponse

router = APIRouter(tags=["Tour Access & Playback Grants"])


async def resolve_subject(request: Request) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Resolves whether request is from an authenticated user or a guest session."""
    user = await get_optional_current_user(token=None, request=request)
    guest = None

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
    token = request.headers.get("X-Device-Token") or request.cookies.get("tourvoice_device_token")
    device = await session_service.verify_device_token(token) if token else None
    device_id = device["_id"] if device and device.get("consent_granted") and "events" in (device.get("consent_scopes") or []) else None

    if not req.tour_id:
        return await access_service.request_poi_grant(req.poi_id, req.lang, req.trigger_source, req.consent_trial, user, guest, req.idempotency_key, device_id)
    res = await access_service.request_playback_grant(
        tour_id=req.tour_id,
        poi_id=req.poi_id,
        lang=req.lang,
        trigger_source=req.trigger_source,
        consent_trial=req.consent_trial,
        idempotency_key=req.idempotency_key,
        user=user,
        guest=guest, device_id=device_id,
    )

    if not res.get("success"):
        err_code = res.get("error", "ACCESS_DENIED")
        status_code = status.HTTP_403_FORBIDDEN
        if err_code == "TOUR_NOT_FOUND" or err_code == "POI_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND
        elif err_code == "AUDIO_UNAVAILABLE":
            status_code = status.HTTP_409_CONFLICT
        elif err_code == "TRIAL_CONSENT_REQUIRED":
            status_code = status.HTTP_403_FORBIDDEN

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": err_code,
                "error_code": err_code,
                "tour_id": req.tour_id,
                "message": res.get("message", "Từ chối truy cập.")
            }
        )

    res["granted"] = True
    return res
