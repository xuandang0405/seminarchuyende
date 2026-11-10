from typing import Optional
from fastapi import APIRouter, Depends
from app.api.v1.endpoints.auth import get_verified_owner
from app.services.rate_limit_service import enforce_rate_limit
from app.schemas.ai import (
    AINarrationRequest,
    AINarrationResponse,
    POIAssistantRequest,
    POIAssistantResponse,
    AIRefineDescriptionRequest,
    AIRefineDescriptionResponse,
    AIMultilingualTranslateRequest,
    AIMultilingualTranslateResponse,
)
from app.services.ai_service import ai_service

async def authorized_editor(current_user: dict = Depends(get_verified_owner)):
    from app.core.config import settings
    from fastapi import HTTPException
    if not settings.GEMINI_API_KEY:
        raise HTTPException(503, "Chưa cấu hình dịch vụ AI. Bạn có thể nhập nội dung thủ công.")
    await enforce_rate_limit("ai:" + current_user["_id"], 30, 86400)
    return current_user


router = APIRouter(prefix="/ai", tags=["AI Narration Assistant"])


@router.post("/generate-narration", response_model=AINarrationResponse)
async def generate_narration(
    req: AINarrationRequest,
    current_user: dict = Depends(authorized_editor)
):
    """
    Sequence Diagram 15 / UseCase C14:
    AI generates rich tourist narration script based on POI keywords, category, and real-time weather context.
    """
    response = await ai_service.generate_narration(req)
    return response


@router.post("/poi-assistant", response_model=POIAssistantResponse)
async def poi_assistant(
    req: POIAssistantRequest,
    current_user: dict = Depends(authorized_editor)
):
    """
    AI POI Assistant:
    Recognizes restaurant / landmark name and auto-generates description,
    address, category, narration script, and specialties.
    """
    return await ai_service.generate_poi_profile(req)


@router.post("/refine-description", response_model=AIRefineDescriptionResponse)
async def refine_description(
    req: AIRefineDescriptionRequest,
    current_user: dict = Depends(authorized_editor)
):
    """
    AI Description Refinement:
    Polishes or enriches existing/new POI description into an enticing 3-5 sentence tourist narrative.
    """
    return await ai_service.refine_poi_description(req)


@router.post("/multilingual-translate", response_model=AIMultilingualTranslateResponse)
async def multilingual_translate(
    req: AIMultilingualTranslateRequest,
    current_user: dict = Depends(authorized_editor)
):
    """
    AI Multilingual Cultural Translation:
    Translates POI name & description into 6 languages (VI, EN, FR, JA, KO, ZH)
    with cultural context for District 4 cuisine and heritage.
    """
    return await ai_service.multilingual_cultural_translate(req)

