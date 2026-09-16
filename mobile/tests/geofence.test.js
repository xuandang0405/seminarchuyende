import test from "node:test";
import assert from "node:assert/strict";
import { GeofenceEngine, calculateDistanceMeters } from "../src/services/GeofenceEngine.js";

test("calculateDistanceMeters: accurate Haversine calculation", () => {
  // Distance between Bến Nhà Rồng (10.76814, 106.70678) and Cầu Mống (10.76895, 106.70488) ~ 226m
  const dist = calculateDistanceMeters(10.76814, 106.70678, 10.76895, 106.70488);
  assert.ok(dist > 200 && dist < 250, `Expected ~226m, got ${dist}`);
});

test("GeofenceEngine: ignores inaccurate GPS samples (> 35m accuracy)", () => {
  const engine = new GeofenceEngine({ accuracyThresholdMeters: 35, debounceMs: 0 });
  const pois = [
    {
      _id: "poi_1",
      name: "Bến Nhà Rồng",
      location: { coordinates: [106.70678, 10.76814] },
      trigger_radius: 30,
      audio_priority: 50,
    },
  ];

  // User is at exact coordinates, but accuracy is 45m (> 35m threshold)
  const result = engine.evaluateLocation(
    { latitude: 10.76814, longitude: 106.70678, accuracy: 45 },
    pois
  );
  assert.equal(result, null, "Should reject sample with accuracy > 35m");
});

test("GeofenceEngine: Debounce requires >= 3s presence before triggering", () => {
  const engine = new GeofenceEngine({ accuracyThresholdMeters: 35, debounceMs: 3000 });
  const pois = [
    {
      _id: "poi_1",
      name: "Bến Nhà Rồng",
      location: { coordinates: [106.70678, 10.76814] },
      trigger_radius: 30,
      audio_priority: 50,
    },
  ];

  // First sample at t = 0
  const r1 = engine.evaluateLocation(
    { latitude: 10.76814, longitude: 106.70678, accuracy: 5 },
    pois
  );
  assert.equal(r1, null, "Should not trigger immediately on first frame");

  // Advance time by 3.1s inside candidate map
  const firstSeen = engine.enteredCandidates.get("poi_1");
  engine.enteredCandidates.set("poi_1", firstSeen - 3100);

  // Next sample after 3s debounce passed
  const r2 = engine.evaluateLocation(
    { latitude: 10.76814, longitude: 106.70678, accuracy: 5 },
    pois
  );
  assert.ok(r2 !== null, "Should trigger after debounce passes");
  assert.equal(r2.poi._id, "poi_1");
});

test("GeofenceEngine: Cooldown prevents repeated triggers for 5 minutes after playback", () => {
  const engine = new GeofenceEngine({ accuracyThresholdMeters: 35, debounceMs: 0, cooldownMs: 300000 });
  const pois = [
    {
      _id: "poi_1",
      name: "Bến Nhà Rồng",
      location: { coordinates: [106.70678, 10.76814] },
      trigger_radius: 30,
    },
  ];

  // Mark playback completed
  engine.markPlaybackCompleted("poi_1");

  // Attempt trigger within cooldown window
  const res = engine.evaluateLocation(
    { latitude: 10.76814, longitude: 106.70678, accuracy: 5 },
    pois
  );
  assert.equal(res, null, "Should not trigger while POI is in cooldown");
});

test("GeofenceEngine: Priority sorting selects higher audio_priority POI", () => {
  const engine = new GeofenceEngine({ accuracyThresholdMeters: 35, debounceMs: 0 });
  const pois = [
    {
      _id: "poi_low",
      name: "Quán Ăn Nhỏ",
      location: { coordinates: [106.70678, 10.76814] },
      trigger_radius: 50,
      audio_priority: 10,
    },
    {
      _id: "poi_high",
      name: "Bến Nhà Rồng Lịch Sử",
      location: { coordinates: [106.70678, 10.76814] },
      trigger_radius: 50,
      audio_priority: 100,
    },
  ];

  const res = engine.evaluateLocation(
    { latitude: 10.76814, longitude: 106.70678, accuracy: 5 },
    pois
  );
  assert.ok(res !== null);
  assert.equal(res.poi._id, "poi_high", "Higher audio_priority must take precedence");
});

test("GeofenceEngine: Stop suppression prevents re-trigger until user exits zone", () => {
  const engine = new GeofenceEngine({ accuracyThresholdMeters: 35, debounceMs: 0 });
  const pois = [
    {
      _id: "poi_1",
      name: "Bến Nhà Rồng",
      location: { coordinates: [106.70678, 10.76814] },
      trigger_radius: 30,
    },
  ];

  // User manually pressed stop while inside zone
  engine.suppressCurrentZone("poi_1");

  // Same location -> suppressed
  const res1 = engine.evaluateLocation(
    { latitude: 10.76814, longitude: 106.70678, accuracy: 5 },
    pois
  );
  assert.equal(res1, null, "Should be suppressed after user pressed stop");

  // User moves 100m away (exits 45m hysteresis radius)
  engine.evaluateLocation(
    { latitude: 10.76950, longitude: 106.70678, accuracy: 5 },
    pois
  );
  assert.equal(engine.suppressedPoiId, null, "Suppression must clear when tourist exits zone");
});
