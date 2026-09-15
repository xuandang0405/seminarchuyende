from fastapi import APIRouter, Depends
from app.api.v1.endpoints.auth import get_current_user
from app.schemas.ai import AINarrationRequest, AINarrationResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["AI Narration Assistant"])


@router.post("/generate-narration", response_model=AINarrationResponse)
async def generate_narration(
    req: AINarrationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Sequence Diagram 15 / UseCase C14:
    AI generates rich tourist narration script based on POI keywords, category, and real-time weather context.
    """
    response = await ai_service.generate_narration(req)
    return response
