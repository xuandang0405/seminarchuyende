"""Router for Guest Sessions & Guest Claiming.

G01 / G03 / BR-ACCESS-02 / BR-ACCESS-04.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.api.v1.endpoints.auth import get_current_user
from app.services.guest_service import guest_service
from app.schemas.guest import GuestSessionCreateResponse, GuestClaimRequest, GuestClaimResponse

router = APIRouter(prefix="/guest-sessions", tags=["Guest Sessions"])

GUEST_COOKIE_NAME = "guest_session_credential"


def set_guest_cookie(response: Response, credential: str):
    response.set_cookie(
        key=GUEST_COOKIE_NAME,
        value=credential,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=30 * 86400,
        path="/",
    )


def clear_guest_cookie(response: Response):
    response.delete_cookie(key=GUEST_COOKIE_NAME, path="/")


@router.post("", response_model=GuestSessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_session(request: Request, response: Response):
    """G01: Creates an anonymous guest session with cryptographically secure credential."""
    client_ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    res = await guest_service.create_guest_session(ip_address=client_ip, user_agent=ua)
    res["guest_token"] = res["guest_credential"]
    set_guest_cookie(response, res["guest_credential"])
    return res


@router.post("/claim", response_model=GuestClaimResponse)
async def claim_guest_session(
    body: GuestClaimRequest,
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """G03: Idempotently claims a guest session to the authenticated user account and merges trial quota."""
    res = await guest_service.claim_guest_session(
        user_id=current_user["_id"],
        guest_credential=body.guest_credential
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("error"))

    clear_guest_cookie(response)
    return res
