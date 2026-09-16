// Geofencing Engine for TourVoice Mobile
// Implements client-side Hysteresis, Debounce, and Cooldown

// In-memory state tracking
const geofenceState = {
  cooldowns: {}, // poiId -> timestamp
  activePoiId: null, // POI currently inside
};

/**
 * Calculates distance in meters between two lat/lng pairs using the Haversine formula.
 */
export function calculateDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371e3; // Earth radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Evaluates user's current GPS position against all active POIs.
 * Returns triggered POI object if an enter condition is satisfied, or null.
 */
export function evaluateGeofences(userLat, userLng, pois = []) {
  const now = Date.now();

  for (const poi of pois) {
    if (!poi.location || !poi.location.coordinates) continue;
    const [poiLng, poiLat] = poi.location.coordinates;
    const distanceMeters = calculateDistanceMeters(userLat, userLng, poiLat, poiLng);

    const enterRadius = poi.radius_enter_m || 30;
    const exitRadius = poi.radius_exit_m || 60;
    const cooldownMs = (poi.cooldown_seconds || 120) * 1000;
    const lastTriggered = geofenceState.cooldowns[poi._id] || 0;

    // Check enter condition
    if (distanceMeters <= enterRadius) {
      if (now - lastTriggered > cooldownMs && geofenceState.activePoiId !== poi._id) {
        geofenceState.cooldowns[poi._id] = now;
        geofenceState.activePoiId = poi._id;
        return {
          poi,
          distanceMeters,
          triggerType: "gps",
        };
      }
    } else if (distanceMeters > exitRadius) {
      // User has exited the hysteresis boundary
      if (geofenceState.activePoiId === poi._id) {
        geofenceState.activePoiId = null;
      }
    }
  }

  return null;
}
