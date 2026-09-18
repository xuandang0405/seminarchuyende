/**
 * NavigationController.js
 *
 * Implements the turn-by-turn Navigation State Machine for Mobile:
 *   IDLE -> PREVIEWING -> NAVIGATING -> REROUTING -> ARRIVED / CANCELLED
 *
 * Requirements:
 * - Single multiplexed location listener
 * - Cross-track distance calculation against route geometry
 * - Re-route debounce & cooldown guard (>= 15s cooldown, >= 2 consecutive off-track samples > 35m)
 * - Arrival threshold: <= 15m from destination
 */

export const NavigationState = {
  IDLE: "IDLE",
  PREVIEWING: "PREVIEWING",
  NAVIGATING: "NAVIGATING",
  REROUTING: "REROUTING",
  ARRIVED: "ARRIVED",
  CANCELLED: "CANCELLED",
  ERROR: "ERROR",
};

/**
 * Calculates straight line distance between two coordinates in meters (Haversine).
 */
export function calculateDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000.0;
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const deltaPhi = ((lat2 - lat1) * Math.PI) / 180;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Calculates shortest distance from point to polyline (cross-track distance) in meters.
 */
export function distanceToPolylineMeters(lat, lon, polylineCoordinates) {
  if (!polylineCoordinates || polylineCoordinates.length === 0) return Infinity;
  let minDist = Infinity;
  for (const pt of polylineCoordinates) {
    // pt can be {latitude, longitude} or [lon, lat]
    const pLat = pt.latitude !== undefined ? pt.latitude : pt[1];
    const pLon = pt.longitude !== undefined ? pt.longitude : pt[0];
    const d = calculateDistanceMeters(lat, lon, pLat, pLon);
    if (d < minDist) {
      minDist = d;
    }
  }
  return minDist;
}

export class NavigationController {
  constructor(options = {}) {
    this.offRouteThresholdMeters = options.offRouteThresholdMeters || 35.0;
    this.consecutiveOffRouteNeeded = options.consecutiveOffRouteNeeded || 2;
    this.rerouteCooldownMs = options.rerouteCooldownMs || 15000;
    this.arrivalThresholdMeters = options.arrivalThresholdMeters || 15.0;

    this.state = NavigationState.IDLE;
    this.currentRoute = null;
    this.destinationPoi = null;
    this.travelMode = "walking";
    this.locale = "vi";

    this.offRouteCount = 0;
    this.lastRerouteTime = 0;
    this.listeners = new Set();
  }

  getState() {
    return {
      state: this.state,
      currentRoute: this.currentRoute,
      destinationPoi: this.destinationPoi,
      travelMode: this.travelMode,
    };
  }

  subscribe(listener) {
    this.listeners.add(listener);
    listener(this.getState());
    return () => this.listeners.delete(listener);
  }

  _notify() {
    const snapshot = this.getState();
    this.listeners.forEach((fn) => {
      try {
        fn(snapshot);
      } catch (err) {
        console.error("[NavigationController] listener error:", err);
      }
    });
  }

  async getApi() {
    if (this.apiClient) return this.apiClient;
    try {
      const mod = await import("./api.js");
      this.apiClient = mod.api;
      return this.apiClient;
    } catch (e) {
      throw new Error("API client is not available in current environment");
    }
  }

  /**
   * Requests route preview from origin to destination POI.
   */
  async previewRoute(originCoords, destinationPoi, mode = "walking", locale = "vi") {
    this.state = NavigationState.PREVIEWING;
    this.destinationPoi = destinationPoi;
    this.travelMode = mode;
    this.locale = locale;
    this._notify();

    try {
      const client = await this.getApi();
      const routeData = await client.getRoutePreview({
        origin: {
          latitude: originCoords.latitude,
          longitude: originCoords.longitude,
        },
        destinationPoiId: destinationPoi._id || destinationPoi.id,
        mode,
        locale,
      });

      this.currentRoute = routeData;
      this._notify();
      return routeData;
    } catch (err) {
      this.state = NavigationState.ERROR;
      this._notify();
      throw err;
    }
  }

  /**
   * Starts live navigation along current previewed route.
   */
  startNavigation() {
    if (!this.currentRoute) {
      throw new Error("Cannot start navigation without a calculated route.");
    }
    this.state = NavigationState.NAVIGATING;
    this.offRouteCount = 0;
    this.lastRerouteTime = Date.now();
    this._notify();
  }

  /**
   * Evaluates user location against active route for arrival and re-routing.
   */
  async updateLocation(userCoords) {
    if (this.state !== NavigationState.NAVIGATING) return;
    if (!this.currentRoute || !this.destinationPoi) return;

    const { latitude, longitude } = userCoords;

    // 1. Check Arrival
    const [destLon, destLat] = this.destinationPoi.location.coordinates;
    const distToDest = calculateDistanceMeters(latitude, longitude, destLat, destLon);
    if (distToDest <= this.arrivalThresholdMeters) {
      this.state = NavigationState.ARRIVED;
      this._notify();
      return;
    }

    // 2. Check Cross-Track Off-Route Distance
    const polyline = this.currentRoute.coordinates || this.currentRoute.geometry?.coordinates;
    const crossTrackDist = distanceToPolylineMeters(latitude, longitude, polyline);

    if (crossTrackDist > this.offRouteThresholdMeters) {
      this.offRouteCount += 1;
    } else {
      this.offRouteCount = 0;
    }

    // 3. Trigger Re-route if threshold met and cooldown passed
    const now = Date.now();
    if (
      this.offRouteCount >= this.consecutiveOffRouteNeeded &&
      now - this.lastRerouteTime >= this.rerouteCooldownMs
    ) {
      console.log(
        `[Navigation] Re-routing triggered! Off-track: ${Math.round(crossTrackDist)}m (${this.offRouteCount} samples)`
      );
      this.state = NavigationState.REROUTING;
      this.lastRerouteTime = now;
      this.offRouteCount = 0;
      this._notify();

      try {
        const client = await this.getApi();
        const newRoute = await client.getRoutePreview({
          origin: { latitude, longitude },
          destinationPoiId: this.destinationPoi._id || this.destinationPoi.id,
          mode: this.travelMode,
          locale: this.locale,
        });
        this.currentRoute = newRoute;
        this.state = NavigationState.NAVIGATING;
        this._notify();
      } catch (err) {
        console.warn("[Navigation] Reroute failed, keeping previous route:", err.message);
        this.state = NavigationState.NAVIGATING;
        this._notify();
      }
    }
  }

  cancelNavigation() {
    this.state = NavigationState.CANCELLED;
    this.currentRoute = null;
    this.destinationPoi = null;
    this.offRouteCount = 0;
    this._notify();
  }
}

export const navigationController = new NavigationController();
