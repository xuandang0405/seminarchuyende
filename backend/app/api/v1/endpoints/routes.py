"""Router for Routing & Directions endpoints (Public, Guest & Authenticated).

Use Cases:
- T14: Yêu cầu chỉ đường đến POI
- T15: Bắt đầu/theo dõi/hủy điều hướng
- T16: So sánh khoảng cách & tính lộ trình giữa 2 POI
- T12/T13: Tuyến đường tour thực tế qua các điểm dừng
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.schemas.routing import (
    RoutePreviewRequest,
    RouteResultDTO,
    TourRouteSummaryResponse,
)
from app.services.routing_service import routing_service
from app.integrations.routing.base import RouteNotFoundError, RoutingUnavailableError

router = APIRouter(prefix="/routes", tags=["Routes & Directions"])


class TourSummaryRequest(BaseModel):
    tour_id: str = Field(..., min_length=1)
    locale: str = "vi"


@router.post("/preview", response_model=RouteResultDTO)
async def preview_route(req: RoutePreviewRequest):
    """Use Case T14 / SD-MAP-05: Calculates normalized route between two coordinates or POIs.

    Open to guests and registered users alike.
    """
    try:
        return await routing_service.get_route_preview(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RouteNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except RoutingUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tính toán tuyến đường: {str(e)}"
        )


@router.post("/tour-summary", response_model=TourRouteSummaryResponse)
async def get_tour_route_summary(req: TourSummaryRequest):
    """Use Case T12/T13: Calculates total distance, duration and geometry for all stops in a tour."""
    try:
        return await routing_service.calculate_tour_legs(tour_id=req.tour_id, locale=req.locale)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tính lộ trình tour: {str(e)}"
        )


@router.get("/tour/{tour_id}", response_model=TourRouteSummaryResponse)
async def get_tour_route_by_id(
    tour_id: str,
    locale: str = Query("vi")
):
    """GET-friendly endpoint for tour route geometry and distance summary."""
    try:
        return await routing_service.calculate_tour_legs(tour_id=tour_id, locale=locale)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tính lộ trình tour: {str(e)}"
        )
