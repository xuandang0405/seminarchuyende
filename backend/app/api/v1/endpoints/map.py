"""Router for Map configuration and public metadata.

Use Case T01 / SD-MAP-01.
"""

from fastapi import APIRouter
from app.core.config import settings
from app.schemas.map import MapConfigResponse, CoordinateDTO, MapBoundsDTO

router = APIRouter(prefix="/map", tags=["Map"])


@router.get("/config", response_model=MapConfigResponse)
async def get_map_config():
    """Returns sanitized runtime map configuration for Web and Mobile clients.

    Includes default center, zoom, bounds for District 4, tile provider, and capabilities.
    """
    return MapConfigResponse(
        center=CoordinateDTO(
            latitude=settings.MAP_DEFAULT_CENTER_LAT,
            longitude=settings.MAP_DEFAULT_CENTER_LNG,
        ),
        default_zoom=settings.MAP_DEFAULT_ZOOM,
        bounds=MapBoundsDTO(
            min_longitude=settings.MAP_BOUNDS_MIN_LNG,
            min_latitude=settings.MAP_BOUNDS_MIN_LAT,
            max_longitude=settings.MAP_BOUNDS_MAX_LNG,
            max_latitude=settings.MAP_BOUNDS_MAX_LAT,
        ),
        tile_provider=settings.MAP_TILE_PROVIDER_NAME,
        style_url=settings.MAP_TILE_STYLE_URL,
        attribution=settings.MAP_ATTRIBUTION,
        capabilities={
            "supports_offline": False,
            "supports_routing": True,
            "supports_search": True,
            "supports_geofencing": True
        }
    )
