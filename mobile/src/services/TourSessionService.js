import AsyncStorage from "@react-native-async-storage/async-storage";
import { analyticsOutbox } from "./AnalyticsOutbox";

const STORAGE_KEY_ACTIVE_TOUR = "tourvoice_active_tour_session";

class TourSessionService {
  constructor() {
    this.activeTour = null;
    this.currentStopIndex = 0;
    this.completedStopIds = new Set();
  }

  async init() {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY_ACTIVE_TOUR);
      if (raw) {
        const data = JSON.parse(raw);
        this.activeTour = data.tour;
        this.currentStopIndex = data.currentStopIndex || 0;
        this.completedStopIds = new Set(data.completedStopIds || []);
      }
    } catch (e) {}
  }

  async startTour(tour) {
    this.activeTour = tour;
    this.currentStopIndex = 0;
    this.completedStopIds = new Set();

    await this.persist();

    analyticsOutbox.recordEvent("tour_started", null, {
      tour_id: tour._id,
      tour_name: tour.name,
      total_stops: (tour.poi_ids || []).length,
    });
  }

  async completeStop(poiId) {
    if (!this.activeTour) return;
    this.completedStopIds.add(poiId);

    const stops = this.activeTour.poi_ids || [];
    if (this.currentStopIndex < stops.length - 1) {
      this.currentStopIndex += 1;
    }

    await this.persist();
  }

  async endTour() {
    if (this.activeTour) {
      analyticsOutbox.recordEvent("tour_ended", null, {
        tour_id: this.activeTour._id,
        completed_count: this.completedStopIds.size,
      });
    }

    this.activeTour = null;
    this.currentStopIndex = 0;
    this.completedStopIds.clear();
    await AsyncStorage.removeItem(STORAGE_KEY_ACTIVE_TOUR);
  }

  async persist() {
    if (!this.activeTour) return;
    const data = {
      tour: this.activeTour,
      currentStopIndex: this.currentStopIndex,
      completedStopIds: Array.from(this.completedStopIds),
    };
    await AsyncStorage.setItem(STORAGE_KEY_ACTIVE_TOUR, JSON.stringify(data));
  }

  getActiveTour() {
    return this.activeTour;
  }

  getNextStopId() {
    if (!this.activeTour || !this.activeTour.poi_ids) return null;
    return this.activeTour.poi_ids[this.currentStopIndex] || null;
  }
}

export const tourSessionService = new TourSessionService();
