"""Protocol definition for Routing Providers."""

from typing import Protocol, Tuple, Dict, Any, Optional
from app.schemas.routing import RouteResultDTO, TravelMode


class RoutingError(Exception):
    """Base exception for routing failures."""
    def __init__(self, message: str, code: str = "ROUTING_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class RouteNotFoundError(RoutingError):
    """Raised when no traversable route is found between origin and destination."""
    def __init__(self, message: str = "Không tìm thấy tuyến đường giữa hai điểm này."):
        super().__init__(message, code="ROUTE_NOT_FOUND")


class RoutingUnavailableError(RoutingError):
    """Raised when the routing backend provider is unreachable, timed out, or rate limited."""
    def __init__(self, message: str = "Dịch vụ chỉ đường hiện không khả dụng. Vui lòng thử lại sau."):
        super().__init__(message, code="ROUTING_UNAVAILABLE")


class RoutingProvider(Protocol):
    """Abstract interface for pluggable routing engines (OSRM, Valhalla, GraphHopper)."""

    async def route(
        self,
        origin: Tuple[float, float],       # (latitude, longitude)
        destination: Tuple[float, float],  # (latitude, longitude)
        mode: TravelMode = TravelMode.WALKING,
        locale: str = "vi",
        alternatives: bool = False,
    ) -> RouteResultDTO:
        """Calculates a route between origin and destination.

        Returns:
            RouteResultDTO: normalized route geometry, distance, duration, steps.

        Raises:
            RouteNotFoundError: if no traversable path exists.
            RoutingUnavailableError: on network, timeout, or provider failure.
        """
        ...
