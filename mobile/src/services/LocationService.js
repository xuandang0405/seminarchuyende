import * as Location from "expo-location";

/**
 * Standardized LocationSample type:
 * {
 *   latitude: number,
 *   longitude: number,
 *   accuracyM: number,
 *   altitudeM: number | null,
 *   headingDeg: number | null,
 *   speedMps: number | null,
 *   capturedAt: string,
 *   source: "current" | "last_known"
 * }
 */
export const LOCATION_PROFILES = {
  map_idle: {
    accuracy: Location.Accuracy.Balanced,
    timeInterval: 6000,
    distanceInterval: 15,
  },
  active_navigation: {
    accuracy: Location.Accuracy.High,
    timeInterval: 2500,
    distanceInterval: 5,
  },
  background_narration: {
    accuracy: Location.Accuracy.High,
    timeInterval: 4000,
    distanceInterval: 10,
  },
};

class LocationService {
  constructor() {
    this.subscription = null;
    this.currentLocation = null;
    this.subscribers = new Set();
    this.hasPermission = false;
    this.permissionState = "prompt"; // "prompt" | "granted" | "denied" | "permanently_denied"
    this.currentProfile = "map_idle";
  }

  _formatSample(coords, source = "current") {
    if (!coords || typeof coords.latitude !== "number" || typeof coords.longitude !== "number") {
      return null;
    }
    if (isNaN(coords.latitude) || isNaN(coords.longitude)) return null;
    if (coords.latitude < -90 || coords.latitude > 90 || coords.longitude < -180 || coords.longitude > 180) {
      return null;
    }

    return {
      latitude: coords.latitude,
      longitude: coords.longitude,
      accuracyM: coords.accuracy || 15.0,
      altitudeM: coords.altitude || null,
      headingDeg: coords.heading != null && coords.heading >= 0 ? coords.heading : null,
      speedMps: coords.speed != null && coords.speed >= 0 ? coords.speed : null,
      capturedAt: new Date().toISOString(),
      source,
    };
  }

  async requestPermission() {
    try {
      const { status, canAskAgain } = await Location.requestForegroundPermissionsAsync();
      if (status === "granted") {
        this.permissionState = "granted";
        this.hasPermission = true;
      } else if (!canAskAgain) {
        this.permissionState = "permanently_denied";
        this.hasPermission = false;
      } else {
        this.permissionState = "denied";
        this.hasPermission = false;
      }
      return this.hasPermission;
    } catch (err) {
      console.warn("[LocationService] Permission request failed:", err.message);
      this.permissionState = "denied";
      this.hasPermission = false;
      return false;
    }
  }

  async getLastKnownLocation() {
    try {
      const last = await Location.getLastKnownPositionAsync({});
      if (last && last.coords) {
        const sample = this._formatSample(last.coords, "last_known");
        if (sample) {
          this.currentLocation = sample;
          return sample;
        }
      }
    } catch (e) {
      // Last known optional
    }
    return null;
  }

  async getCurrentLocation() {
    if (!this.hasPermission) {
      const granted = await this.requestPermission();
      if (!granted) return null;
    }

    // Try last known first for quick display
    if (!this.currentLocation) {
      await this.getLastKnownLocation();
    }

    try {
      const loc = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      const sample = this._formatSample(loc.coords, "current");
      if (sample) {
        this.currentLocation = sample;
      }
      return this.currentLocation;
    } catch (err) {
      console.warn("[LocationService] getCurrentLocation error:", err.message);
      return this.currentLocation;
    }
  }

  setProfile(profileName = "map_idle") {
    if (LOCATION_PROFILES[profileName] && this.currentProfile !== profileName) {
      this.currentProfile = profileName;
      if (this.subscribers.size > 0) {
        this._restartWatching();
      }
    }
  }

  async _restartWatching() {
    if (this.subscription) {
      this.subscription.remove();
      this.subscription = null;
    }

    const cfg = LOCATION_PROFILES[this.currentProfile] || LOCATION_PROFILES.map_idle;

    try {
      this.subscription = await Location.watchPositionAsync(
        {
          accuracy: cfg.accuracy,
          timeInterval: cfg.timeInterval,
          distanceInterval: cfg.distanceInterval,
        },
        (location) => {
          const sample = this._formatSample(location.coords, "current");
          if (!sample) return;

          // Outlier & teleport guard
          if (this.currentLocation && sample.accuracyM <= 50) {
            const timeDiffSec = (new Date(sample.capturedAt) - new Date(this.currentLocation.capturedAt)) / 1000;
            if (timeDiffSec > 0 && timeDiffSec < 3) {
              const dLat = Math.abs(sample.latitude - this.currentLocation.latitude);
              const dLng = Math.abs(sample.longitude - this.currentLocation.longitude);
              // Jump of > ~500m in under 3 seconds = impossible walking/driving speed in city (166m/s = 600km/h)
              if (dLat > 0.005 || dLng > 0.005) {
                console.warn("[LocationService] Outlier teleport sample ignored.");
                return;
              }
            }
          }

          this.currentLocation = sample;
          for (const sub of this.subscribers) {
            try {
              sub(sample);
            } catch (e) {
              console.error("[LocationService] subscriber error:", e);
            }
          }
        }
      );
    } catch (err) {
      console.warn("[LocationService] startWatching error:", err.message);
    }
  }

  async startWatching(onLocationUpdate, options = {}) {
    if (!this.hasPermission) {
      const granted = await this.requestPermission();
      if (!granted) return null;
    }

    if (onLocationUpdate) {
      this.subscribers.add(onLocationUpdate);
      if (this.currentLocation) {
        onLocationUpdate(this.currentLocation);
      }
    }

    if (!this.subscription) {
      await this._restartWatching();
    }

    // Return unsubscribe handle
    return () => {
      this.unsubscribe(onLocationUpdate);
    };
  }

  unsubscribe(onLocationUpdate) {
    if (onLocationUpdate) {
      this.subscribers.delete(onLocationUpdate);
    }
    if (this.subscribers.size === 0) {
      this.stopWatching();
    }
  }

  stopWatching() {
    if (this.subscription) {
      this.subscription.remove();
      this.subscription = null;
    }
  }
}

export const locationService = new LocationService();

