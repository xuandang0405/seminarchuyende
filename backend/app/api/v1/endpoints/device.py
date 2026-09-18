"""Endpoint for Device Identity Bootstrap.

Implements Section 9 / BR-DEVICE-01 / BR-DEVICE-02.
"""

from fastapi import APIRouter, Cookie, Header, Response, status
from typing import Optional

from app.schemas.device_session import (
    DeviceBootstrapRequest,
    DeviceBootstrapResponse,
)
from app.services.session_service import session_service

router = APIRouter(prefix="/device", tags=["Device Identity"])


@router.post("/bootstrap", response_model=DeviceBootstrapResponse, status_code=status.HTTP_200_OK)
async def bootstrap_device_endpoint(
    req: DeviceBootstrapRequest,
    response: Response,
    cookie_token: Optional[str] = Cookie(None, alias="tourvoice_device_token"),
    header_token: Optional[str] = Header(None, alias="x-device-token"),
):
    """Issues or recovers a cryptographic device identity.
    
    Accepts existing token from JSON body, X-Device-Token header, or HttpOnly cookie.
    Sets HttpOnly secure cookie for web clients.
    """
    token = req.device_token or header_token or cookie_token
    device_doc, raw_token, is_new = await session_service.bootstrap_device(
        device_token=token,
        platform=req.platform.value if hasattr(req.platform, "value") else str(req.platform),
        app_version=req.app_version
    )

    # Set first-party cookie for browser clients
    response.set_cookie(
        key="tourvoice_device_token",
        value=raw_token,
        max_age=365 * 24 * 3600,  # 1 year
        httponly=True,
        samesite="lax",
        secure=False  # Set True in HTTPS production
    )

    return DeviceBootstrapResponse(
        device_id=device_doc["_id"],
        device_token=raw_token,
        created_at=device_doc.get("created_at") or device_doc.get("first_seen_at"),
        is_new=is_new
    )
