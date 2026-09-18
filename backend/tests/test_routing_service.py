"""Unit & Integration tests for RoutingService and OSRM Provider."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.schemas.routing import (
    RoutePreviewRequest,
    RouteResultDTO,
    RouteLegDTO,
    RouteStepDTO,
    CoordinateDTO,
    TravelMode,
)
from app.services.routing_service import (
    RoutingService,
    generate_route_fingerprint,
)
from app.integrations.routing.osrm_provider import OSRMRoutingProvider
from app.integrations.routing.base import RouteNotFoundError, RoutingUnavailableError


def test_fingerprint_deterministic_and_quantized():
    """Points within ~11 meters (quantized 4 decimals) produce the exact same fingerprint."""
    # Bến Nhà Rồng slightly shifted by 0.00002 deg (~2m)
    fp1 = generate_route_fingerprint(10.76814, 106.70678, 10.76890, 106.70420, "walking", "vi")
    fp2 = generate_route_fingerprint(10.768142, 106.706781, 10.768903, 106.704204, "walking", "vi")
    assert fp1 == fp2

    # Different mode produces different fingerprint
    fp_driving = generate_route_fingerprint(10.76814, 106.70678, 10.76890, 106.70420, "driving", "vi")
    assert fp1 != fp_driving


@pytest.mark.asyncio
async def test_micro_distance_short_circuit():
    """Distance < 8m short-circuits without external network request."""
    provider = OSRMRoutingProvider()
    result = await provider.route(
        origin=(10.76814, 106.70678),
        destination=(10.76814, 106.70678),
        mode=TravelMode.WALKING,
        locale="vi"
    )
    assert result.route_distance_m == 0.0
    assert result.route_duration_s == 0.0
    assert result.distance_display == "0 m"
    assert "ngay điểm đến" in result.steps[0].instruction


@pytest.mark.asyncio
async def test_osrm_normalizer_mock():
    """Validates normalization of OSRM response into RouteResultDTO with Vietnamese steps."""
    mock_osrm_response = {
        "code": "Ok",
        "routes": [
            {
                "distance": 325.4,
                "duration": 240.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [106.70678, 10.76814],
                        [106.70550, 10.76850],
                        [106.70420, 10.76890]
                    ]
                },
                "legs": [
                    {
                        "distance": 325.4,
                        "duration": 240.0,
                        "steps": [
                            {
                                "name": "Nguyễn Tất Thành",
                                "distance": 150.0,
                                "duration": 110.0,
                                "maneuver": {"type": "depart", "modifier": ""}
                            },
                            {
                                "name": "Bến Vân Đồn",
                                "distance": 175.4,
                                "duration": 130.0,
                                "maneuver": {"type": "turn", "modifier": "left"}
                            },
                            {
                                "name": "",
                                "distance": 0.0,
                                "duration": 0.0,
                                "maneuver": {"type": "arrive", "modifier": ""}
                            }
                        ]
                    }
                ]
            }
        ],
        "waypoints": [
            {"distance": 1.2, "name": "Nguyễn Tất Thành"},
            {"distance": 2.5, "name": "Bến Vân Đồn"}
        ]
    }

    provider = OSRMRoutingProvider()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_osrm_response
        mock_get.return_value = mock_response

        res = await provider.route(
            origin=(10.76814, 106.70678),
            destination=(10.76890, 106.70420),
            mode=TravelMode.WALKING,
            locale="vi"
        )

        assert res.route_distance_m == 325.4
        assert res.route_duration_s == 240.0
        assert res.distance_display == "325 m"
        assert res.duration_display == "4 phút"
        assert res.geometry["type"] == "LineString"
        assert len(res.coordinates) == 3
        assert len(res.steps) == 3
        assert "Bắt đầu đi" in res.steps[0].instruction
        assert "Rẽ trái" in res.steps[1].instruction
        assert "Đã đến điểm tham quan" in res.steps[2].instruction


@pytest.mark.asyncio
async def test_routing_service_cache_hit():
    """When a cached route exists, RoutingService returns it without calling the provider."""
    mock_provider = AsyncMock()
    service = RoutingService(provider=mock_provider)

    req = RoutePreviewRequest(
        origin=CoordinateDTO(latitude=10.76814, longitude=106.70678),
        destination=CoordinateDTO(latitude=10.76890, longitude=106.70420),
        mode=TravelMode.WALKING,
        locale="vi"
    )

    cached_route_data = {
        "route_id": "route_cached_123",
        "mode": "walking",
        "route_distance_m": 300.0,
        "route_duration_s": 220.0,
        "distance_display": "300 m",
        "duration_display": "4 phút",
        "geometry": {"type": "LineString", "coordinates": [[106.70678, 10.76814], [106.70420, 10.76890]]},
        "coordinates": [[106.70678, 10.76814], [106.70420, 10.76890]],
        "legs": [],
        "steps": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch("app.repositories.route_cache_repo.route_cache_repo.get_by_fingerprint", new_callable=AsyncMock) as mock_get_cache:
        mock_get_cache.return_value = {"route": cached_route_data}

        result = await service.get_route_preview(req)
        assert result.route_id == "route_cached_123"
        assert result.route_distance_m == 300.0
        # Provider should NOT be called on cache hit
        mock_provider.route.assert_not_called()
