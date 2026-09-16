import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "./api";

const STORAGE_KEY_OUTBOX = "tourvoice_analytics_outbox";
const STORAGE_KEY_CONSENT = "tourvoice_analytics_consent";
const STORAGE_KEY_SESSION = "tourvoice_analytics_session_id";

function generateUUID() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

class AnalyticsOutboxService {
  constructor() {
    this.consent = false;
    this.sessionId = null;
    this.isFlushing = false;
    this.init();
  }

  async init() {
    try {
      const consentVal = await AsyncStorage.getItem(STORAGE_KEY_CONSENT);
      // Default to true or whatever was saved
      this.consent = consentVal !== null ? JSON.parse(consentVal) : true;

      let sess = await AsyncStorage.getItem(STORAGE_KEY_SESSION);
      if (!sess) {
        sess = `sess_${generateUUID()}`;
        await AsyncStorage.setItem(STORAGE_KEY_SESSION, sess);
      }
      this.sessionId = sess;
    } catch (e) {
      this.consent = false;
    }
  }

  async setConsent(enabled) {
    this.consent = enabled;
    await AsyncStorage.setItem(STORAGE_KEY_CONSENT, JSON.stringify(enabled));
    if (!enabled) {
      // Clear local outbox when consent is revoked (UC F08 / AD11)
      await AsyncStorage.removeItem(STORAGE_KEY_OUTBOX);
    }
  }

  async getConsent() {
    const consentVal = await AsyncStorage.getItem(STORAGE_KEY_CONSENT);
    return consentVal !== null ? JSON.parse(consentVal) : true;
  }

  /**
   * Enqueues an analytics event if user gave consent.
   * Event types: "poi_view", "audio_play", "audio_progress", "audio_completed", "tour_started", "qr_scanned".
   */
  async recordEvent(eventType, poiId = null, properties = {}) {
    if (!this.consent) return;

    try {
      const event = {
        _id: generateUUID(),
        session_id: this.sessionId || "default_session",
        poi_id: poiId,
        event_type: eventType,
        occurred_at: new Date().toISOString(),
        properties,
      };

      const raw = await AsyncStorage.getItem(STORAGE_KEY_OUTBOX);
      const queue = raw ? JSON.parse(raw) : [];
      queue.push(event);

      // Keep max 200 events in local storage to prevent unbounded growth
      if (queue.length > 200) {
        queue.splice(0, queue.length - 200);
      }

      await AsyncStorage.setItem(STORAGE_KEY_OUTBOX, JSON.stringify(queue));

      // Trigger background flush if queue size >= 5
      if (queue.length >= 5) {
        this.flush();
      }
    } catch (err) {
      console.warn("[AnalyticsOutbox] Failed to record event:", err.message);
    }
  }

  /**
   * Flushes queued events to FastAPI backend with per-event ACK
   */
  async flush() {
    if (!this.consent || this.isFlushing) return;
    this.isFlushing = true;

    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY_OUTBOX);
      if (!raw) {
        this.isFlushing = false;
        return;
      }

      const queue = JSON.parse(raw);
      if (queue.length === 0) {
        this.isFlushing = false;
        return;
      }

      // Batch up to 20 events
      const batch = queue.slice(0, 20);
      const res = await api.sendAnalyticsBatch(batch);

      if (res && res.success) {
        const processedIds = new Set(res.processed_ids || batch.map((e) => e._id));
        const remaining = queue.filter((e) => !processedIds.has(e._id));
        await AsyncStorage.setItem(STORAGE_KEY_OUTBOX, JSON.stringify(remaining));
      }
    } catch (err) {
      console.warn("[AnalyticsOutbox] Flush error:", err.message);
    } finally {
      this.isFlushing = false;
    }
  }
}

export const analyticsOutbox = new AnalyticsOutboxService();
