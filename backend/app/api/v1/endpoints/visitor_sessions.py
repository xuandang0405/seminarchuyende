"""Router for Visitor Sessions (analytics_sessions).

Implements Section 10.2 / BR-SESSION-01:
- Start or idempotent resume per device.
- Lightweight conditional heartbeat.
- Explicit session termination.
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Header, HTTPException, status

from app.schemas.device_session import (
    VisitorSessionStartRequest,
    VisitorSessionResponse,
)
from app.services.session_service import session_service

router = APIRouter(prefix="/visitor-sessions", tags=["Visitor Sessions"])


async def _resolve_device_id(
    body_token: Optional[str],
    header_token: Optional[str],
    cookie_token: Optional[str],
    platform: str = "web",
) -> str:
    """Helper to verify token or bootstrap an anonymous device identity."""
    token = body_token or header_token or cookie_token
    device_doc, _, _ = await session_service.bootstrap_device(
        device_token=token,
        platform=platform
    )
    return device_doc["_id"]


@router.post("/start-or-resume", response_model=VisitorSessionResponse, status_code=status.HTTP_200_OK)
async def start_or_resume_visitor_session(
    req: VisitorSessionStartRequest,
    cookie_token: Optional[str] = Cookie(None, alias="tourvoice_device_token"),
    header_token: Optional[str] = Header(None, alias="x-device-token"),
):
    """Starts a new visitor session or idempotently resumes an active one for the same device."""
    platform_str = req.platform.value if hasattr(req.platform, "value") else str(req.platform)
    device_id = await _resolve_device_id(
        body_token=req.device_token,
        header_token=header_token,
        cookie_token=cookie_token,
        platform=platform_str
    )

    sess = await session_service.start_or_resume_visitor_session(
        device_id=device_id,
        platform=platform_str,
        app_version=req.app_version,
        locale=req.locale,
        consent_granted=req.consent_granted,
        consent_version=req.consent_version
    )
    return sess


@router.post("/{session_id}/heartbeat")
async def visitor_session_heartbeat(
    session_id: str,
    cookie_token: Optional[str] = Cookie(None, alias="tourvoice_device_token"),
    header_token: Optional[str] = Header(None, alias="x-device-token"),
):
    """Conditional heartbeat updating last_seen_at with device ownership verification."""
    token = header_token or cookie_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu device token để gửi heartbeat."
        )

    device_doc = await session_service.verify_device_token(token)
    if not device_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device token không hợp lệ."
        )

    updated = await session_service.heartbeat_visitor_session(
        session_id=session_id,
        device_id=device_doc["_id"]
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên làm việc không tồn tại hoặc đã kết thúc."
        )

    return {
        "status": "active",
        "session_id": session_id,
        "last_seen_at": updated["last_seen_at"].isoformat()
    }


@router.post("/{session_id}/end")
async def end_visitor_session_endpoint(
    session_id: str,
    cookie_token: Optional[str] = Cookie(None, alias="tourvoice_device_token"),
    header_token: Optional[str] = Header(None, alias="x-device-token"),
):
    """Explicitly terminates an active visitor session."""
    token = header_token or cookie_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu device token để kết thúc phiên."
        )

    device_doc = await session_service.verify_device_token(token)
    if not device_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device token không hợp lệ."
        )

    ended = await session_service.end_visitor_session(
        session_id=session_id,
        device_id=device_doc["_id"]
    )
    if not ended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên làm việc không tồn tại hoặc đã kết thúc."
        )

    return {
        "status": "ended",
        "session_id": session_id,
        "ended_at": ended["ended_at"].isoformat()
    }
