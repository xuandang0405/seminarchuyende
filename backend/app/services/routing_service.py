"""Routing service orchestrator: validation, POI resolution, caching, and tour routing."""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional, Tuple

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

_MEMORY_ROUTE_CACHE: dict[str, tuple[float, RouteResultDTO]] = {}
_MEMORY_CACHE_TTL_SECONDS = 3600


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
    raw_key = f"osrm-profile-v2:{qlat1:.4f},{qlon1:.4f}->{qlat2:.4f},{qlon2:.4f}:{mode}:{locale}"
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

        return await self._cached_route(fingerprint, mode_str, lambda: self.provider.route(
            origin=(origin_lat, origin_lon), destination=(dest_lat, dest_lon),
            mode=req.mode, locale=req.locale,
        ))

    async def _cached_route(
        self,
        fingerprint: str,
        mode: str,
        calculate: Callable[[], Awaitable[RouteResultDTO]],
    ) -> RouteResultDTO:
        now_ts = time.time()
        if fingerprint in _MEMORY_ROUTE_CACHE:
            expire_at, mem_route = _MEMORY_ROUTE_CACHE[fingerprint]
            if now_ts < expire_at:
                return mem_route
            else:
                _MEMORY_ROUTE_CACHE.pop(fingerprint, None)

        cached = await route_cache_repo.get_by_fingerprint(fingerprint)
        if cached and "route" in cached:
            try:
                dto = RouteResultDTO(**cached["route"])
                _MEMORY_ROUTE_CACHE[fingerprint] = (now_ts + _MEMORY_CACHE_TTL_SECONDS, dto)
                return dto
            except Exception as e:
                logger.warning(f"Could not deserialize cached route: {e}")

        route_dto = await calculate()
        _MEMORY_ROUTE_CACHE[fingerprint] = (now_ts + _MEMORY_CACHE_TTL_SECONDS, route_dto)

        try:
            await route_cache_repo.save_route(
                fingerprint=fingerprint,
                mode=mode,
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
        """Route through ordered tour stops with a single request per waypoint batch."""
        tour = await tour_repo.get_by_id(tour_id)
        if not tour:
            raise ValueError(f"Không tìm thấy tour có mã: {tour_id}")

        poi_ids = tour.get("poi_ids", [])
        points: list[tuple[float, float]] = []
        geometry: list[list[float]] = []
        legs: list[dict[str, Any]] = []
        total_distance = total_duration = 0.0
        limit = max(2, settings.ROUTING_MAX_POINTS_PER_REQUEST)
        for start in range(0, len(poi_ids) - 1, limit - 1):
            ids = poi_ids[start:start + limit]
            try:
                if not points:
                    resolved = await asyncio.gather(*(self._resolve_coordinate(None, id_) for id_ in ids))
                else:
                    # Reuse the shared endpoint between consecutive batches.
                    resolved = await asyncio.gather(*(self._resolve_coordinate(None, id_) for id_ in ids[1:]))
                batch = (points[-1:] if start else []) + [(lat, lon) for lat, lon, _ in resolved]
                points.extend(batch[1:] if start else batch)
                key = json.dumps(["tour-waypoints-v1", batch, mode.value, locale], separators=(",", ":"))
                fingerprint = hashlib.sha256(key.encode()).hexdigest()
                route = await self._cached_route(
                    fingerprint, mode.value, lambda: self.provider.route_waypoints(batch, mode, locale),
                )
                if len(route.legs) != len(ids) - 1:
                    raise RoutingUnavailableError("Dịch vụ chỉ đường trả thiếu chặng.")
            except (ValueError, RouteNotFoundError, RoutingUnavailableError) as error:
                logger.warning("Could not calculate tour %s at leg %s: %s", tour_id, start + 1, error)
                # Publish only a diagram for the stops already resolved. The UI
                # distinguishes this from a valid route via the missing legs.
                geometry = [[lon, lat] for lat, lon in points]
                legs.clear()
                total_distance = total_duration = 0.0
                break

            total_distance += route.route_distance_m
            total_duration += route.route_duration_s
            coordinates = route.coordinates or route.geometry["coordinates"]
            geometry.extend(coordinates[1:] if geometry and geometry[-1] == coordinates[0] else coordinates)
            for index, leg in enumerate(route.legs):
                legs.append({
                    "leg_index": start + index + 1,
                    "from_poi_id": ids[index],
                    "to_poi_id": ids[index + 1],
                    "distance_m": leg.distance_m,
                    "duration_s": leg.duration_s,
                    "distance_display": leg.distance_display,
                    "duration_display": leg.duration_display,
                    "step_count": len(leg.steps),
                    "steps": [step.model_dump(mode="json") for step in leg.steps],
                })

        return TourRouteSummaryResponse(
            tour_id=tour_id,
            tour_name=tour.get("name", "Tour Tham Quan"),
            stop_count=len(poi_ids),
            total_distance_m=round(total_distance, 1),
            total_duration_s=round(total_duration, 1),
            total_distance_display=format_distance_display(total_distance, lang=locale),
            total_duration_display=format_duration_display(total_duration, lang=locale),
            geometry={"type": "LineString", "coordinates": geometry},
            legs=legs,
        )


routing_service = RoutingService()
