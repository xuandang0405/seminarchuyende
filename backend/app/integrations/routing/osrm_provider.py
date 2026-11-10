"""OSRM (Open Source Routing Machine) routing provider implementation."""

import asyncio
import inspect
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
from urllib.parse import urlsplit
import httpx

from app.core.config import settings
from app.integrations.routing.base import (
    RoutingProvider,
    RouteNotFoundError,
    RoutingUnavailableError,
)
from app.schemas.routing import (
    RouteResultDTO,
    RouteLegDTO,
    RouteStepDTO,
    TravelMode,
)
from app.services.geo_service import (
    haversine_distance_meters,
    format_distance_display,
    format_duration_display,
    validate_coordinates,
)

logger = logging.getLogger("uvicorn")


class OSRMRoutingProvider(RoutingProvider):
    """Integrates with OSRM HTTP Route service (v5.24+)."""

    def __init__(self, base_url: str = None, timeout_s: float = None):
        self.base_url = (base_url or settings.ROUTING_PROVIDER_URL).rstrip("/")
        self.timeout_s = timeout_s or settings.ROUTING_TIMEOUT_SECONDS
        self._demo_lock = asyncio.Lock()
        self._next_demo_request = 0.0

    def base_url_for(self, mode: TravelMode) -> str:
        profile = self._map_profile(mode)
        server = "car" if mode == TravelMode.DRIVING else profile
        # The old public OSRM host runs a car graph even for a /foot request.
        if self.base_url == "https://router.project-osrm.org" and mode != TravelMode.DRIVING:
            return f"https://routing.openstreetmap.de/routed-{server}"
        return self.base_url.replace("{mode}", server)

    async def _pace_demo_requests(self) -> None:
        async with self._demo_lock:
            loop = asyncio.get_running_loop()
            delay = self._next_demo_request - loop.time()
            if 0 < delay <= 1.05:
                await asyncio.sleep(delay)
            self._next_demo_request = loop.time() + 0.4

    def _map_profile(self, mode: TravelMode) -> str:
        """Maps travel mode enum to OSRM service profile."""
        if mode == TravelMode.DRIVING:
            return "driving"
        elif mode == TravelMode.CYCLING:
            return "bike"
        # Default walking / foot
        return "foot"

    def _translate_maneuver(self, step: Dict[str, Any], lang: str) -> str:
        """Produces friendly instruction from OSRM maneuver object."""
        maneuver = step.get("maneuver", {})
        m_type = maneuver.get("type", "turn")
        modifier = maneuver.get("modifier", "")
        name = step.get("name") or ("đường đi" if lang == "vi" else "street")

        if lang == "vi":
            if m_type == "depart":
                return f"Bắt đầu đi từ {name}"
            if m_type == "arrive":
                return "Đã đến điểm tham quan"
            if m_type == "turn":
                if "left" in modifier:
                    return f"Rẽ trái vào {name}"
                elif "right" in modifier:
                    return f"Rẽ phải vào {name}"
                return f"Rẽ vào {name}"
            if m_type == "continue" or m_type == "new name":
                return f"Đi thẳng tiếp tục trên {name}"
            if "roundabout" in m_type or "rotary" in m_type:
                return f"Vào bùng binh, đi theo lối ra vào {name}"
            return f"Đi tiếp vào {name}"
        else:
            if m_type == "depart":
                return f"Depart on {name}"
            if m_type == "arrive":
                return "Arrived at destination"
            if m_type == "turn":
                if "left" in modifier:
                    return f"Turn left onto {name}"
                elif "right" in modifier:
                    return f"Turn right onto {name}"
                return f"Turn onto {name}"
            return f"Continue onto {name}"

    async def route(
        self,
        origin: Tuple[float, float],       # (lat, lon)
        destination: Tuple[float, float],  # (lat, lon)
        mode: TravelMode = TravelMode.WALKING,
        locale: str = "vi",
        alternatives: bool = False,
    ) -> RouteResultDTO:
        return await self.route_waypoints([origin, destination], mode, locale)

    async def route_waypoints(
        self,
        points: list[tuple[float, float]],
        mode: TravelMode = TravelMode.WALKING,
        locale: str = "vi",
    ) -> RouteResultDTO:
        if len(points) < 2:
            raise ValueError("Cần ít nhất hai điểm để tính lộ trình.")
        for latitude, longitude in points:
            validate_coordinates(latitude, longitude)
        (lat1, lon1), (lat2, lon2) = points[0], points[-1]

        # Micro-distance short-circuit (< 8 meters)
        straight_dist = sum(haversine_distance_meters(*a, *b) for a, b in zip(points, points[1:]))
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=settings.ROUTING_CACHE_TTL_HOURS)

        if len(points) == 2 and straight_dist < 8.0:
            return RouteResultDTO(
                route_id=f"route_{uuid.uuid4().hex[:12]}",
                mode=mode.value,
                route_distance_m=0.0,
                route_duration_s=0.0,
                distance_display="0 m",
                duration_display="< 1 phút" if locale == "vi" else "< 1 min",
                geometry={
                    "type": "LineString",
                    "coordinates": [[lon1, lat1], [lon2, lat2]]
                },
                coordinates=[[lon1, lat1], [lon2, lat2]],
                legs=[
                    RouteLegDTO(
                        distance_m=0.0,
                        duration_s=0.0,
                        distance_display="0 m",
                        duration_display="< 1 phút" if locale == "vi" else "< 1 min",
                        steps=[
                            RouteStepDTO(
                                instruction="Bạn đang ở ngay điểm đến" if locale == "vi" else "You have arrived",
                                distance_m=0.0,
                                duration_s=0.0,
                                distance_display="0 m",
                                duration_display="0s",
                                street_name="",
                                maneuver_type="arrive"
                            )
                        ]
                    )
                ],
                steps=[
                    RouteStepDTO(
                        instruction="Bạn đang ở ngay điểm đến" if locale == "vi" else "You have arrived",
                        distance_m=0.0,
                        duration_s=0.0,
                        distance_display="0 m",
                        duration_display="0s",
                        street_name="",
                        maneuver_type="arrive"
                    )
                ],
                generated_at=now,
                expires_at=expires_at,
            )

        profile = self._map_profile(mode)
        base_url = self.base_url_for(mode)
        # OSRM follows the supplied waypoint order and returns one leg per pair.
        coordinates = ";".join(f"{longitude:.6f},{latitude:.6f}" for latitude, longitude in points)
        url = (
            f"{base_url}/route/v1/{profile}/{coordinates}"
            f"?overview=full&geometries=geojson&steps=true&annotations=false"
        )
        headers = {
            "User-Agent": "TourVoice-App/1.0 (Tourism Navigation System Quan 4; contact: support@tourvoice.vn)"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s, limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)) as client:
                if urlsplit(base_url).hostname == "routing.openstreetmap.de":
                    await self._pace_demo_requests()
                res = await client.get(url, headers=headers)
        except httpx.TimeoutException:
            logger.warning(f"OSRM Routing timeout ({self.timeout_s}s) for {url}")
            raise RoutingUnavailableError("Thời gian kết nối đến máy chủ chỉ đường quá hạn. Vui lòng thử lại sau.")
        except Exception as e:
            logger.error(f"OSRM Routing connection error: {e}")
            raise RoutingUnavailableError("Không thể kết nối đến hệ thống định tuyến đường bộ thực tế.")

        if res.status_code == 400:
            data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
            msg = data.get("message", "Tọa độ không hợp lệ hoặc nằm ngoài mạng lưới đường.")
            raise RouteNotFoundError(msg)

        if res.status_code != 200:
            raise RoutingUnavailableError(f"Máy chủ định tuyến phản hồi lỗi mã {res.status_code}.")

        data = res.json()
        if inspect.iscoroutine(data):
            data = await data
        code = data.get("code")

        if code == "NoRoute":
            raise RouteNotFoundError("Không tìm thấy đường bộ nối hai địa điểm này.")
        if code != "Ok" or not data.get("routes"):
            raise RouteNotFoundError("Không tìm thấy đường đi khả dụng.")

        raw_route = data["routes"][0]
        route_dist_m = float(raw_route.get("distance", straight_dist))
        route_dur_s = float(raw_route.get("duration", (route_dist_m / 1.1)))  # default 1.1 m/s walk
        geometry = raw_route.get("geometry") or {}
        line_coords = geometry.get("coordinates", [])
        if geometry.get("type") != "LineString" or len(line_coords) < 2:
            raise RoutingUnavailableError("Máy chủ định tuyến chưa trả về tuyến đường hợp lệ.")

        # Parse legs and steps
        parsed_legs: List[RouteLegDTO] = []
        all_steps: List[RouteStepDTO] = []

        for leg_data in raw_route.get("legs", []):
            leg_dist = float(leg_data.get("distance", route_dist_m))
            leg_dur = float(leg_data.get("duration", route_dur_s))
            leg_steps: List[RouteStepDTO] = []

            for step_data in leg_data.get("steps", []):
                s_dist = float(step_data.get("distance", 0.0))
                s_dur = float(step_data.get("duration", 0.0))
                instruction = self._translate_maneuver(step_data, locale)
                maneuver_type = step_data.get("maneuver", {}).get("type", "turn")
                street_name = step_data.get("name", "")

                step_dto = RouteStepDTO(
                    instruction=instruction,
                    distance_m=round(s_dist, 1),
                    duration_s=round(s_dur, 1),
                    distance_display=format_distance_display(s_dist, lang=locale),
                    duration_display=format_duration_display(s_dur, lang=locale),
                    street_name=street_name,
                    maneuver_type=maneuver_type
                )
                leg_steps.append(step_dto)
                all_steps.append(step_dto)

            parsed_legs.append(RouteLegDTO(
                distance_m=round(leg_dist, 1),
                duration_s=round(leg_dur, 1),
                distance_display=format_distance_display(leg_dist, lang=locale),
                duration_display=format_duration_display(leg_dur, lang=locale),
                steps=leg_steps
            ))

        # Snapped distance calculations
        waypoints = data.get("waypoints", [])
        snapped_orig_dist = 0.0
        snapped_dest_dist = 0.0
        if len(waypoints) >= 2:
            snapped_orig_dist = float(waypoints[0].get("distance", 0.0))
            snapped_dest_dist = float(waypoints[-1].get("distance", 0.0))

        route_id = f"route_{uuid.uuid4().hex[:12]}"
        return RouteResultDTO(
            route_id=route_id,
            mode=mode.value,
            route_distance_m=round(route_dist_m, 1),
            route_duration_s=round(route_dur_s, 1),
            distance_display=format_distance_display(route_dist_m, lang=locale),
            duration_display=format_duration_display(route_dur_s, lang=locale),
            geometry=geometry,
            coordinates=line_coords,
            legs=parsed_legs,
            steps=all_steps,
            snapped_origin_distance_m=round(snapped_orig_dist, 1),
            snapped_destination_distance_m=round(snapped_dest_dist, 1),
            generated_at=now,
            expires_at=expires_at,
        )


osrm_provider = OSRMRoutingProvider()
