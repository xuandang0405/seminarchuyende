import * as Location from "expo-location";

class LocationService {
  constructor() {
    this.subscription = null;
    this.currentLocation = null;
    this.listeners = new Set();
    this.hasPermission = false;
  }

  async requestPermission() {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      this.hasPermission = status === "granted";
      return this.hasPermission;
    } catch (err) {
      console.warn("[LocationService] Permission request failed:", err.message);
      this.hasPermission = false;
      return false;
    }
  }

  async getCurrentLocation() {
    if (!this.hasPermission) {
      const granted = await this.requestPermission();
      if (!granted) return null;
    }

    try {
      const loc = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      this.currentLocation = loc.coords;
      return this.currentLocation;
    } catch (err) {
      console.warn("[LocationService] getCurrentLocation error:", err.message);
      return null;
    }
  }

  async startWatching(onLocationUpdate, { timeInterval = 3000, distanceInterval = 5 } = {}) {
    if (!this.hasPermission) {
      const granted = await this.requestPermission();
      if (!granted) return null;
    }

    if (this.subscription) {
      this.subscription.remove();
      this.subscription = null;
    }

    try {
      this.subscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval,
          distanceInterval,
        },
        (location) => {
          this.currentLocation = location.coords;
          if (onLocationUpdate) {
            onLocationUpdate(location.coords);
          }
        }
      );
      return this.subscription;
    } catch (err) {
      console.warn("[LocationService] startWatching error:", err.message);
      return null;
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
