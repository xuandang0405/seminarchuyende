"""Routing service orchestrator: validation, POI resolution, caching, and tour routing."""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.integrations.routing.osrm_provider import osrm_provider
from app.integrations.routing.base import RouteNotFoundError, RoutingUnavailableError
from app.repositories.poi_repo import poi_repo
from app.repositories.tour_repo import tour_repo
from app.repositories.route_cache_repo import route_cache_repo
from app.schemas.routing import (
    RoutePreviewRequest,
    RouteResultDTO,
    TourRouteSummaryResponse,
    TravelMode,
)
from app.services.geo_service import (
    quantize_coordinate,
    validate_coordinates,
    format_distance_display,
    format_duration_display,
)

logger = logging.getLogger("uvicorn")


def generate_route_fingerprint(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    mode: str,
    locale: str = "vi"
) -> str:
    """Generates a quantized deterministic MD5 fingerprint for route caching."""
    qlat1, qlon1 = quantize_coordinate(lat1, lon1, precision=4)
    qlat2, qlon2 = quantize_coordinate(lat2, lon2, precision=4)
    raw_key = f"{qlat1:.4f},{qlon1:.4f}->{qlat2:.4f},{qlon2:.4f}:{mode}:{locale}"
    return hashlib.md5(raw_key.encode("utf-8")).hexdigest()


class RoutingService:
    def __init__(self, provider=None):
        self.provider = provider or osrm_provider

    async def _resolve_coordinate(
        self,
        coord_dto: Optional[Any],
        poi_id: Optional[str]
    ) -> Tuple[float, float, str]:
        """Resolves either explicit CoordinateDTO or POI ID to (latitude, longitude, label)."""
        if poi_id:
            poi = await poi_repo.get_public_by_id(poi_id)
            if not poi:
                # Also try regular get_by_id for admin preview
                poi = await poi_repo.get_by_id(poi_id)
            if not poi:
                raise ValueError(f"Không tìm thấy địa điểm POI có mã: {poi_id}")
            loc = poi.get("location", {}).get("coordinates")
            if not loc or len(loc) < 2:
                raise ValueError(f"POI {poi_id} không có tọa độ hợp lệ.")
            lat, lon = float(loc[1]), float(loc[0])
            label = poi.get("name") or poi.get("code") or poi_id
            validate_coordinates(lat, lon)
            return lat, lon, label

        if coord_dto:
            lat = float(coord_dto.latitude)
            lon = float(coord_dto.longitude)
            validate_coordinates(lat, lon)
            return lat, lon, f"({lat:.5f}, {lon:.5f})"

        raise ValueError("Cần cung cấp tọa độ hoặc ID điểm tham quan.")

    async def get_route_preview(self, req: RoutePreviewRequest) -> RouteResultDTO:
        """Calculates normalized route between origin and destination with caching."""
        origin_lat, origin_lon, _ = await self._resolve_coordinate(req.origin, req.origin_poi_id)
        dest_lat, dest_lon, _ = await self._resolve_coordinate(req.destination, req.destination_poi_id)

        mode_str = req.mode.value if isinstance(req.mode, TravelMode) else str(req.mode)
        fingerprint = generate_route_fingerprint(
            origin_lat, origin_lon, dest_lat, dest_lon, mode_str, req.locale
        )

        # 1. Check cache
        cached = await route_cache_repo.get_by_fingerprint(fingerprint)
        if cached and "route" in cached:
            try:
                return RouteResultDTO(**cached["route"])
            except Exception as e:
                logger.warning(f"Could not deserialize cached route: {e}")

        # 2. Query Routing Engine
        route_dto = await self.provider.route(
            origin=(origin_lat, origin_lon),
            destination=(dest_lat, dest_lon),
            mode=req.mode,
            locale=req.locale,
        )

        # 3. Save to cache
        try:
            await route_cache_repo.save_route(
                fingerprint=fingerprint,
                mode=mode_str,
                route_data=route_dto.model_dump(mode="json"),
                ttl_hours=settings.ROUTING_CACHE_TTL_HOURS
            )
        except Exception as e:
            logger.warning(f"Failed to cache route: {e}")

        return route_dto

    async def calculate_tour_legs(
        self,
        tour_id: str,
        locale: str = "vi",
        mode: TravelMode = TravelMode.WALKING
    ) -> TourRouteSummaryResponse:
        """Calculates the actual walking route across all stops in a tour sequentially."""
        tour = await tour_repo.get_by_id(tour_id)
        if not tour:
            raise ValueError(f"Không tìm thấy tour có mã: {tour_id}")

        poi_ids = tour.get("poi_ids", [])
        tour_name = tour.get("name", "Tour Tham Quan")

        if len(poi_ids) < 2:
            return TourRouteSummaryResponse(
                tour_id=tour_id,
                tour_name=tour_name,
                stop_count=len(poi_ids),
                total_distance_m=0.0,
                total_duration_s=0.0,
                total_distance_display="0 m",
                total_duration_display="< 1 phút" if locale == "vi" else "< 1 min",
                geometry={"type": "LineString", "coordinates": []},
                legs=[]
            )

        total_dist_m = 0.0
        total_dur_s = 0.0
        combined_coords: List[List[float]] = []
        legs_summary: List[Dict[str, Any]] = []

        for i in range(len(poi_ids) - 1):
            from_poi_id = poi_ids[i]
            to_poi_id = poi_ids[i + 1]

            try:
                preview_req = RoutePreviewRequest(
                    origin_poi_id=from_poi_id,
                    destination_poi_id=to_poi_id,
                    mode=mode,
                    locale=locale
                )
                leg_route = await self.get_route_preview(preview_req)
                leg_coords = leg_route.coordinates or leg_route.geometry.get("coordinates", [])

                total_dist_m += leg_route.route_distance_m
                total_dur_s += leg_route.route_duration_s

                # Stitch line coordinates without duplicating joining vertex
                if not combined_coords:
                    combined_coords.extend(leg_coords)
                else:
                    if leg_coords:
                        combined_coords.extend(leg_coords[1:] if len(leg_coords) > 1 else leg_coords)

                legs_summary.append({
                    "leg_index": i + 1,
                    "from_poi_id": from_poi_id,
                    "to_poi_id": to_poi_id,
                    "distance_m": leg_route.route_distance_m,
                    "duration_s": leg_route.route_duration_s,
                    "distance_display": leg_route.distance_display,
                    "duration_display": leg_route.duration_display,
                    "step_count": len(leg_route.steps)
                })
            except Exception as e:
                logger.warning(f"Error calculating leg {from_poi_id} -> {to_poi_id}: {e}")
                # Provide straight-line fallback for this leg if network down
                try:
                    poi_a = await poi_repo.get_by_id(from_poi_id)
                    poi_b = await poi_repo.get_by_id(to_poi_id)
                    loc_a = poi_a.get("location", {}).get("coordinates", [106.7, 10.7])
                    loc_b = poi_b.get("location", {}).get("coordinates", [106.7, 10.7])
                    combined_coords.extend([loc_a, loc_b])
                except Exception:
                    pass

        return TourRouteSummaryResponse(
            tour_id=tour_id,
            tour_name=tour_name,
            stop_count=len(poi_ids),
            total_distance_m=round(total_dist_m, 1),
            total_duration_s=round(total_dur_s, 1),
            total_distance_display=format_distance_display(total_dist_m, lang=locale),
            total_duration_display=format_duration_display(total_dur_s, lang=locale),
            geometry={"type": "LineString", "coordinates": combined_coords},
            legs=legs_summary
        )


routing_service = RoutingService()
