"""Router for Map configuration and public metadata.

Use Case T01 / SD-MAP-01.
"""

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from urllib.parse import urlsplit
from app.core.config import settings
from app.schemas.map import MapConfigResponse, CoordinateDTO, MapBoundsDTO

router = APIRouter(prefix="/map", tags=["Map"])
packs_router = APIRouter(prefix="/maps", tags=["Map"])
manifest_file = Path(__file__).resolve().parents[5] / "apps/web-admin/dist/static/maps/packs/current/manifest.json"


def _read_offline_manifest(response: Response):
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Chưa công bố gói bản đồ.") from exc
    response.headers["Cache-Control"] = "no-cache"
    return manifest


@packs_router.get("/offline-manifest")
def offline_manifest(response: Response):
    return _read_offline_manifest(response)


@packs_router.get("/offline-options")
def offline_options(response: Response):
    return {"items": [_read_offline_manifest(response)]}


@router.get("/config", response_model=MapConfigResponse)
async def get_map_config():
    """Returns sanitized runtime map configuration for Web and Mobile clients.

    Includes default center, zoom, bounds for District 4, tile provider, and capabilities.
    """
    style_url, provider, attribution = settings.MAP_TILE_STYLE_URL, settings.MAP_TILE_PROVIDER_NAME, settings.MAP_ATTRIBUTION
    try:
        parsed = urlsplit(style_url.replace("{s}", "0"))
        valid = (parsed.scheme == "https" and parsed.hostname

                 and all(f"{{{axis}}}" in style_url for axis in ("x", "y", "z")))
    except Exception:
        valid = False
    if not valid:
        style_url = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        provider = "OpenStreetMap"
        attribution = "© OpenStreetMap contributors"
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
        tile_provider=provider,
        style_url=style_url,
        attribution=attribution,
        capabilities={
            "supports_offline": False,
            "supports_routing": True,
            "supports_search": True,
            "supports_geofencing": True
        }
    )
