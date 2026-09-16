/**
 * Pure Geofence Engine for TourVoice Mobile
 * Implements Hysteresis, 3-second Debounce, 5-minute Cooldown, Accuracy Filter,
 * and Audio Priority sorting (Section 14 & SD04/AD04).
 * Pure JavaScript - no React components imported.
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

export class GeofenceEngine {
  constructor({
    accuracyThresholdMeters = 35,
    debounceMs = 3000,
    cooldownMs = 300000, // 5 minutes
  } = {}) {
    this.accuracyThresholdMeters = accuracyThresholdMeters;
    this.debounceMs = debounceMs;
    this.cooldownMs = cooldownMs;

    // Cooldown map: poiId -> timestamp of last successful playback
    this.cooldowns = new Map();
    // Debounce map: poiId -> timestamp of first detected entrance
    this.enteredCandidates = new Map();
    // Active POI ID inside boundary (for exit hysteresis)
    this.activePoiId = null;
    // Suppressed POI ID (when user pressed STOP while still inside zone)
    this.suppressedPoiId = null;
  }

  /**
   * Called by NarrationController after audio playback finishes successfully.
   * Cooldown is strictly applied AFTER playback, not on trigger.
   */
  markPlaybackCompleted(poiId) {
    this.cooldowns.set(poiId, Date.now());
  }

  /**
   * If user explicitly stops audio, suppress auto re-trigger until user exits zone.
   */
  suppressCurrentZone(poiId) {
    this.suppressedPoiId = poiId;
  }

  /**
   * Evaluates current GPS location against POI list.
   * Returns winning POI candidate or null.
   */
  evaluateLocation(userLocation, pois = []) {
    if (!userLocation || !pois || pois.length === 0) return null;

    const { latitude, longitude, accuracy } = userLocation;

    // 1. Accuracy Filter: discard inaccurate GPS samples (> 35m)
    if (accuracy && accuracy > this.accuracyThresholdMeters) {
      return null;
    }

    const now = Date.now();
    const matchingCandidates = [];

    for (const poi of pois) {
      if (!poi.location || !poi.location.coordinates) continue;

      const [poiLng, poiLat] = poi.location.coordinates;
      const distance = calculateDistanceMeters(latitude, longitude, poiLat, poiLng);

      const triggerRadius = poi.trigger_radius || 30;
      const exitRadius = triggerRadius * 1.5;

      const lastPlayed = this.cooldowns.get(poi._id) || 0;
      const isCoolingDown = now - lastPlayed < this.cooldownMs;

      // Check Exit Hysteresis: user has moved outside exitRadius
      if (distance > exitRadius) {
        this.enteredCandidates.delete(poi._id);
        if (this.activePoiId === poi._id) {
          this.activePoiId = null;
        }
        if (this.suppressedPoiId === poi._id) {
          this.suppressedPoiId = null; // Unsuppress now that user left zone
        }
        continue;
      }

      // Check Entrance Condition
      if (distance <= triggerRadius) {
        if (isCoolingDown) continue;
        if (this.suppressedPoiId === poi._id) continue;

        // 2. Debounce Check: verify user stayed inside for >= debounceMs
        if (!this.enteredCandidates.has(poi._id)) {
          this.enteredCandidates.set(poi._id, now);
        }

        const firstSeen = this.enteredCandidates.get(poi._id);
        if (now - firstSeen >= this.debounceMs) {
          matchingCandidates.push({
            poi,
            distance,
            priority: poi.audio_priority ?? 50,
          });
        }
      }
    }

    if (matchingCandidates.length === 0) return null;

    // 3. Priority Sorting: Highest audio_priority first, then closest distance
    matchingCandidates.sort((a, b) => {
      if (b.priority !== a.priority) {
        return b.priority - a.priority; // higher priority wins
      }
      return a.distance - b.distance; // closer distance wins
    });

    const winner = matchingCandidates[0];
    this.activePoiId = winner.poi._id;
    return {
      poi: winner.poi,
      distance: winner.distance,
      triggerType: "gps",
    };
  }

  reset() {
    this.cooldowns.clear();
    this.enteredCandidates.clear();
    this.activePoiId = null;
    this.suppressedPoiId = null;
  }
}

export const geofenceEngine = new GeofenceEngine();
