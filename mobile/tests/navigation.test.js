import test from "node:test";
import assert from "node:assert/strict";
import {
  NavigationController,
  NavigationState,
  calculateDistanceMeters,
  distanceToPolylineMeters,
} from "../src/services/NavigationController.js";

test("calculateDistanceMeters: accurate Haversine calculation for District 4", () => {
  // Bến Nhà Rồng (10.76814, 106.70678) to Cầu Mống (10.76890, 106.70420) ~ 295m
  const dist = calculateDistanceMeters(10.76814, 106.70678, 10.76890, 106.70420);
  assert.ok(dist >= 280 && dist <= 320, `Expected ~295m, got ${dist}`);
});

test("distanceToPolylineMeters: detects proximity to polyline", () => {
  const line = [
    [106.70678, 10.76814], // [lon, lat]
    [106.70420, 10.76890],
  ];

  // User is right at point 1
  const d1 = distanceToPolylineMeters(10.76814, 106.70678, line);
  assert.ok(d1 < 1.0, `Expected ~0m, got ${d1}`);

  // User is 500m away
  const d2 = distanceToPolylineMeters(10.76000, 106.70000, line);
  assert.ok(d2 > 400, `Expected > 400m, got ${d2}`);
});

test("NavigationController: detects arrival within arrivalThresholdMeters (15m)", async () => {
  const controller = new NavigationController({ arrivalThresholdMeters: 15.0 });
  const poi = {
    _id: "poi_dest",
    name: "Cầu Mống",
    location: { coordinates: [106.70420, 10.76890] },
  };

  controller.destinationPoi = poi;
  controller.currentRoute = {
    route_distance_m: 295,
    coordinates: [[106.70678, 10.76814], [106.70420, 10.76890]],
  };
  controller.state = NavigationState.NAVIGATING;

  // User moves to 5m away from destination
  await controller.updateLocation({ latitude: 10.76892, longitude: 106.70422 });
  assert.equal(controller.state, NavigationState.ARRIVED, "State should transition to ARRIVED");
});

test("NavigationController: off-track counter requires >= 2 consecutive samples before rerouting", async () => {
  const controller = new NavigationController({
    offRouteThresholdMeters: 35.0,
    consecutiveOffRouteNeeded: 2,
    rerouteCooldownMs: 1000,
  });

  const poi = {
    _id: "poi_dest",
    name: "Cầu Mống",
    location: { coordinates: [106.70420, 10.76890] },
  };

  controller.destinationPoi = poi;
  controller.currentRoute = {
    route_distance_m: 295,
    coordinates: [[106.70678, 10.76814], [106.70420, 10.76890]],
  };
  controller.state = NavigationState.NAVIGATING;
  controller.lastRerouteTime = Date.now() - 5000; // cooldown elapsed

  // Sample 1: 50m off route
  await controller.updateLocation({ latitude: 10.76500, longitude: 106.70500 });
  assert.equal(controller.offRouteCount, 1);
  assert.equal(controller.state, NavigationState.NAVIGATING, "Should NOT reroute on only 1 off-track sample");
});
