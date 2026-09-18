/**
 * Shared LocationService for Web Client.
 * 
 * Implements Section 4 / BR-GEO-01 / BR-GEO-02 / BR-GEO-03:
 * - Single shared watchPosition with multiplexed subscribers & reference counting.
 * - Standardized LocationSample type with accuracy, heading, and capturedAt.
 * - Outlier & teleport filtering, signal degradation warnings.
 * - Configurable profiles: 'map_idle', 'active_navigation', 'background_narration'.
 */

class LocationService {
  constructor() {
    this.subscribers = new Set();
    this.watchId = null;
    this.lastSample = null;
    this.permissionState = "prompt"; // "prompt" | "granted" | "denied" | "unavailable"
    this.activeProfile = "map_idle";
    this.isGeolocationSupported = typeof navigator !== "undefined" && "geolocation" in navigator;
    
    // Profiles
    this.profiles = {
      map_idle: { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 },
      active_navigation: { enableHighAccuracy: true, timeout: 5000, maximumAge: 2000 },
      background_narration: { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 }
    };
  }

  /**
   * Validates and normalizes raw GeolocationPosition to LocationSample.
   * BR-GEO-01: -90 <= lat <= 90 and -180 <= lon <= 180, non-NaN.
   */
  _normalizeSample(coords, timestamp, source = "current") {
    const lat = Number(coords.latitude);
    const lon = Number(coords.longitude);
    const accuracy = Number(coords.accuracy || 15.0);

    if (isNaN(lat) || isNaN(lon) || isNaN(accuracy)) return null;
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;

    // BR-GEO-02: Outlier teleport check against last sample
    if (this.lastSample && source === "current") {
      const timeDiffSec = (timestamp - new Date(this.lastSample.capturedAt).getTime()) / 1000.0;
      if (timeDiffSec > 0 && timeDiffSec < 3.0) {
        // Approximate distance in meters
        const dLat = (lat - this.lastSample.latitude) * 111000.0;
        const dLon = (lon - this.lastSample.longitude) * 111000.0 * Math.cos((lat * Math.PI) / 180.0);
        const distM = Math.sqrt(dLat * dLat + dLon * dLon);
        const speedMps = distM / timeDiffSec;
        // If impossible jump (> 60 m/s ~ 216 km/h for pedestrian tourist) with low accuracy, ignore
        if (speedMps > 60 && accuracy > 30) {
          console.warn("[LocationService] Ignored teleport outlier:", { distM, speedMps, accuracy });
          return null;
        }
      }
    }

    const sample = {
      latitude: Number(lat.toFixed(6)),
      longitude: Number(lon.toFixed(6)),
      accuracyM: Math.round(accuracy),
      altitudeM: coords.altitude != null ? Math.round(coords.altitude) : null,
      headingDeg: coords.heading != null && !isNaN(coords.heading) && coords.heading >= 0 ? Math.round(coords.heading) : null,
      speedMps: coords.speed != null && !isNaN(coords.speed) && coords.speed >= 0 ? Math.round(coords.speed * 10) / 10 : null,
      capturedAt: new Date(timestamp).toISOString(),
      source: source
    };

    return sample;
  }

  /**
   * Checks browser Geolocation permission status via Permissions API where available.
   */
  async checkPermission() {
    if (!this.isGeolocationSupported) {
      this.permissionState = "unavailable";
      return this.permissionState;
    }

    if (typeof navigator.permissions !== "undefined" && navigator.permissions.query) {
      try {
        const status = await navigator.permissions.query({ name: "geolocation" });
        this.permissionState = status.state; // "granted" | "denied" | "prompt"
        status.onchange = () => {
          this.permissionState = status.state;
          this._notifySubscribers(this.lastSample);
        };
      } catch (e) {
        // Fallback for browsers that don't support geolocation permission query
      }
    }
    return this.permissionState;
  }

  /**
   * Sets current sampling profile ('map_idle' | 'active_navigation' | 'background_narration').
   */
  setProfile(profileName) {
    if (this.profiles[profileName] && this.activeProfile !== profileName) {
      this.activeProfile = profileName;
      if (this.watchId !== null) {
        // Restart watcher with new profile options
        this._stopWatch();
        this._startWatch();
      }
    }
  }

  /**
   * Subscribes a listener callback to the location stream.
   * Implements reference-counted watcher initialization.
   * Returns an unsubscribe function.
   */
  subscribe(callback) {
    if (typeof callback !== "function") return () => {};

    this.subscribers.add(callback);

    // If lastSample exists, notify immediately as last_known
    if (this.lastSample) {
      try {
        callback({ ...this.lastSample, source: "last_known" });
      } catch (err) {
        console.error("[LocationService] Subscriber error:", err);
      }
    }

    // Start single shared watcher if first subscriber
    if (this.subscribers.size === 1 && this.watchId === null) {
      this._startWatch();
    }

    return () => this.unsubscribe(callback);
  }

  /**
   * Unsubscribes a listener callback. Cleans up watchPosition when subscriber count drops to 0.
   */
  unsubscribe(callback) {
    this.subscribers.delete(callback);
    if (this.subscribers.size === 0 && this.watchId !== null) {
      this._stopWatch();
    }
  }

  _startWatch() {
    if (!this.isGeolocationSupported) {
      this.permissionState = "unavailable";
      return;
    }

    const options = this.profiles[this.activeProfile] || this.profiles.map_idle;

    this.watchId = navigator.geolocation.watchPosition(
      (pos) => {
        this.permissionState = "granted";
        const sample = this._normalizeSample(pos.coords, pos.timestamp, "current");
        if (sample) {
          this.lastSample = sample;
          this._notifySubscribers(sample);
        }
      },
      (err) => {
        if (err.code === 1) {
          this.permissionState = "denied";
        }
        console.warn("[LocationService] Position error:", err.code, err.message);
      },
      options
    );
  }

  _stopWatch() {
    if (this.watchId !== null) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }
  }

  _notifySubscribers(sample) {
    for (const sub of this.subscribers) {
      try {
        sub(sample);
      } catch (err) {
        console.error("[LocationService] Subscriber error:", err);
      }
    }
  }

  /**
   * One-time position fetch (promises).
   */
  getCurrentPosition() {
    return new Promise((resolve, reject) => {
      if (!this.isGeolocationSupported) {
        reject(new Error("Trình duyệt không hỗ trợ Geolocation"));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this.permissionState = "granted";
          const sample = this._normalizeSample(pos.coords, pos.timestamp, "current");
          if (sample) {
            this.lastSample = sample;
            resolve(sample);
          } else {
            reject(new Error("Tọa độ thu được không hợp lệ."));
          }
        },
        (err) => {
          if (err.code === 1) this.permissionState = "denied";
          reject(err);
        },
        this.profiles[this.activeProfile]
      );
    });
  }
}

// Export singleton on window
if (typeof window !== "undefined") {
  window.tourvoiceLocation = new LocationService();
}
