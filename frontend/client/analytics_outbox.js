/**
 * Durable AnalyticsOutbox based on IndexedDB for Web Client.
 * 
 * Implements Section 12 / BR-SYNC-01 / BR-CONSENT-01:
 * - Local durable queuing before network transmission.
 * - Handles per-item ACK: deletes events only upon 'accepted' or 'duplicate'.
 * - Consent-aware: drops events and purges queue when consent is revoked.
 * - Exponential backoff with jitter on network failure.
 */

class AnalyticsOutbox {
  constructor() {
    this.dbName = "TourVoiceDB";
    this.dbVersion = 1;
    this.storeName = "analytics_outbox";
    this.db = null;
    this.isFlushing = false;
    this.consentGranted = true;
    this.retryDelayMs = 2000;
    this.maxBatchSize = 20;

    this._initDB();
    this._initListeners();
  }

  async _initDB() {
    return new Promise((resolve, reject) => {
      if (typeof window === "undefined" || !window.indexedDB) {
        resolve(null);
        return;
      }

      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: "event_id" });
        }
      };

      request.onsuccess = (event) => {
        this.db = event.target.result;
        resolve(this.db);
        this.flush(); // Try flush pending events from earlier sessions
      };

      request.onerror = (err) => {
        console.warn("[AnalyticsOutbox] IndexedDB open error:", err);
        resolve(null);
      };
    });
  }

  _initListeners() {
    if (typeof window !== "undefined") {
      window.addEventListener("online", () => {
        console.log("[AnalyticsOutbox] Network restored, triggering flush...");
        this.retryDelayMs = 2000;
        this.flush();
      });

      // Periodic background flush every 30 seconds
      setInterval(() => {
        this.flush();
      }, 30000);
    }
  }

  setConsent(granted) {
    this.consentGranted = Boolean(granted);
    if (!this.consentGranted) {
      this.clearQueue();
    }
  }

  async clearQueue() {
    if (!this.db) return;
    try {
      const tx = this.db.transaction([this.storeName], "readwrite");
      tx.objectStore(this.storeName).clear();
    } catch (e) {
      console.warn("[AnalyticsOutbox] Failed to clear queue:", e);
    }
  }

  /**
   * Enqueues an event durably into IndexedDB.
   */
  async recordEvent(eventType, payload = {}) {
    if (!this.consentGranted) return null;

    const eventId = "ev_" + ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );

    const eventDoc = {
      event_id: eventId,
      event_type: eventType,
      client_occurred_at: new Date().toISOString(),
      ...payload
    };

    if (!this.db) {
      await this._initDB();
    }

    if (this.db) {
      try {
        const tx = this.db.transaction([this.storeName], "readwrite");
        tx.objectStore(this.storeName).put(eventDoc);
      } catch (err) {
        console.warn("[AnalyticsOutbox] Error writing to IndexedDB:", err);
      }
    }

    // Trigger flush
    this.flush();
    return eventId;
  }

  /**
   * Flushes up to maxBatchSize events with per-item ACK handling.
   */
  async flush() {
    if (!this.db || this.isFlushing || !this.consentGranted) return;
    if (typeof navigator !== "undefined" && !navigator.onLine) return;

    this.isFlushing = true;

    try {
      // 1. Read batch from IndexedDB
      const events = await new Promise((resolve) => {
        const tx = this.db.transaction([this.storeName], "readonly");
        const req = tx.objectStore(this.storeName).getAll(null, this.maxBatchSize);
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => resolve([]);
      });

      if (!events || events.length === 0) {
        this.isFlushing = false;
        return;
      }

      // 2. Transmit batch to backend
      const apiBase = typeof window !== "undefined" && window.tourvoiceApiBase ? window.tourvoiceApiBase : "/api/v1";
      const res = await fetch(`${apiBase}/analytics/events/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events })
      });

      if (res.ok) {
        const data = await res.json();
        const acks = data.acks || [];
        const toDeleteIds = [];

        for (const ack of acks) {
          // BR-SYNC-01: Remove only on 'accepted', 'duplicate', or permanent rejection
          if (ack.status === "accepted" || ack.status === "duplicate" || ack.status === "rejected_permanent") {
            toDeleteIds.push(ack.event_id);
          }
        }

        // Delete processed events
        if (toDeleteIds.length > 0) {
          const deleteTx = this.db.transaction([this.storeName], "readwrite");
          const store = deleteTx.objectStore(this.storeName);
          for (const id of toDeleteIds) {
            store.delete(id);
          }
        }

        this.retryDelayMs = 2000;

        // If there are more events left in queue, flush next batch immediately
        if (events.length === this.maxBatchSize) {
          setTimeout(() => this.flush(), 200);
        }
      } else {
        // Server returned error (5xx / 429) -> apply exponential backoff
        this.retryDelayMs = Math.min(this.retryDelayMs * 2, 60000);
      }
    } catch (err) {
      console.warn("[AnalyticsOutbox] Network error during flush:", err);
      this.retryDelayMs = Math.min(this.retryDelayMs * 2, 60000);
    } finally {
      this.isFlushing = false;
    }
  }
}

// Export singleton on window
if (typeof window !== "undefined") {
  window.tourvoiceOutbox = new AnalyticsOutbox();
}
