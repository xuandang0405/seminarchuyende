import { geofenceEngine } from "./GeofenceEngine";
import { audioSourceResolver } from "./AudioSourceResolver";
import { analyticsOutbox } from "./AnalyticsOutbox";
import { api } from "./api";

// Defensively require expo-audio to prevent native module crashes in Expo Go
let ExpoAudio = null;
try {
  ExpoAudio = require("expo-audio");
} catch (err) {
  console.warn("[NarrationController] expo-audio native module not available:", err?.message);
}

export const NarrationState = {
  IDLE: "idle",
  QUEUED: "queued",
  LOADING: "loading",
  PLAYING: "playing",
  PAUSED: "paused",
  STOPPING: "stopping",
  ERROR: "error",
};

class NarrationController {
  constructor() {
    this.player = null;
    this.state = NarrationState.IDLE;
    this.currentPoi = null;
    this.triggerType = "manual"; // "manual" | "qr" | "gps"
    this.audioTitle = "";
    this.audioSubtitle = "";
    this.currentLang = "vi";
    this.playbackId = null;
    this.playStartTime = 0;
    this.listenedMs = 0;
    this.listeners = new Set();
    this.configuredAudioMode = false;
    this.activeTourId = "tour_district_4_culinary_history";
    this.userToken = null;
    this.guestToken = null;
    this.lastErrorCode = null;
    this.statusSubscription = null;
    this.simulationTimer = null;
  }

  setSession(userToken, guestToken, tourId = null) {
    this.userToken = userToken;
    this.guestToken = guestToken;
    if (tourId) this.activeTourId = tourId;
  }

  subscribe(listener) {
    this.listeners.add(listener);
    listener(this.getStateSnapshot());
    return () => this.listeners.delete(listener);
  }

  notify() {
    const snapshot = this.getStateSnapshot();
    for (const listener of this.listeners) {
      listener(snapshot);
    }
  }

  getStateSnapshot() {
    return {
      state: this.state,
      poi: this.currentPoi,
      triggerType: this.triggerType,
      title: this.audioTitle,
      subtitle: this.audioSubtitle,
      isPlaying: this.state === NarrationState.PLAYING,
      isLoading: this.state === NarrationState.LOADING || this.state === NarrationState.QUEUED,
      lastErrorCode: this.lastErrorCode,
      activeTourId: this.activeTourId,
    };
  }

  async ensureAudioMode() {
    if (this.configuredAudioMode) return;
    if (ExpoAudio && typeof ExpoAudio.setAudioModeAsync === "function") {
      try {
        await ExpoAudio.setAudioModeAsync({
          playsInSilentMode: true,
          shouldPlayInBackground: true,
        });
        this.configuredAudioMode = true;
      } catch (e) {
        console.warn("[NarrationController] setAudioModeAsync notice:", e.message);
      }
    }
  }

  /**
   * Main request method to play narration.
   * Priority: "manual" or "qr" preempts "gps".
   */
  async requestNarration(poi, triggerType = "manual", lang = "vi", userConsentTrial = false) {
    if (!poi) return;

    // GPS cannot interrupt active manual or QR playback
    if (
      triggerType === "gps" &&
      this.triggerType !== "gps" &&
      (this.state === NarrationState.PLAYING || this.state === NarrationState.LOADING)
    ) {
      return;
    }

    // If same POI is already playing, keep playing
    if (
      this.currentPoi &&
      this.currentPoi._id === poi._id &&
      this.state === NarrationState.PLAYING
    ) {
      return;
    }

    await this.stop();

    this.currentPoi = poi;
    this.triggerType = triggerType;
    this.currentLang = lang;
    this.audioTitle = poi.name || "Điểm Thuyết Minh";
    this.audioSubtitle = poi.description || poi.address || "";
    this.state = NarrationState.LOADING;
    this.lastErrorCode = null;
    this.playbackId = `pb_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    this.listenedMs = 0;
    this.notify();

    try {
      await this.ensureAudioMode();

      // Resolve audio source
      const source = await audioSourceResolver.resolveAudioSource(poi, lang);
      let playbackUri = source?.uri;

      // If source is remote HTTP, verify access grant
      if (source && source.sourceType === "remote" && playbackUri && playbackUri.startsWith("http")) {
        const tourId = this.activeTourId || poi.tour_id || "tour_district_4_culinary_history";
        try {
          const grantRes = await api.requestPlaybackGrant({
            tourId,
            poiId: poi._id,
            language: lang,
            triggerType,
            userConsentTrial,
          }, this.guestToken, this.userToken);

          if (!grantRes.ok || !grantRes.data?.granted) {
            const errorCode = grantRes.data?.error_code || "TOUR_PURCHASE_REQUIRED";
            this.lastErrorCode = errorCode;
            this.state = NarrationState.ERROR;

            if (errorCode === "TRIAL_CONSENT_REQUIRED") {
              this.audioSubtitle = "💡 Bạn còn 1 lượt nghe thử miễn phí. Bấm Xác Nhận để nghe thuyết minh.";
            } else {
              this.audioSubtitle = "🔒 Đã hết lượt nghe thử. Vui lòng mua tour để mở khóa toàn bộ nội dung.";
            }
            this.notify();
            return;
          }

          const grantToken = grantRes.data?.grant_token;
          if (grantToken) {
            const delim = playbackUri.includes("?") ? "&" : "?";
            playbackUri = `${playbackUri}${delim}grant_token=${grantToken}`;
          }
        } catch (grantErr) {
          console.warn("[NarrationController] Playback grant check notice:", grantErr.message);
        }
      }

      // 1. Play with expo-audio if available
      if (ExpoAudio && typeof ExpoAudio.createAudioPlayer === "function" && playbackUri) {
        const player = ExpoAudio.createAudioPlayer(playbackUri);
        this.player = player;

        if (typeof player.addListener === "function") {
          this.statusSubscription = player.addListener("playbackStatusUpdate", (status) => {
            if (status.playbackState === "ended" || (status.duration > 0 && status.currentTime >= status.duration)) {
              this.onPlaybackFinished(status.duration || 10);
            }
          });
        }

        player.play();
        this.state = NarrationState.PLAYING;
        this.playStartTime = Date.now();
        this.notify();
      } else {
        // 2. Resilient Simulation Mode (if native audio driver is absent in current Expo Go)
        console.log("[NarrationController] Running resilient audio narration playback:", playbackUri);
        this.state = NarrationState.PLAYING;
        this.playStartTime = Date.now();
        this.notify();

        const durationSec = 15;
        this.simulationTimer = setTimeout(() => {
          this.onPlaybackFinished(durationSec);
        }, durationSec * 1000);
      }

      // Record analytics event
      analyticsOutbox.recordEvent("audio_play", poi._id, {
        playback_id: this.playbackId,
        trigger_type: triggerType,
        lang,
        source_type: source?.sourceType || "remote",
      });
    } catch (err) {
      console.warn("[NarrationController] Playback error:", err.message);
      this.state = NarrationState.ERROR;
      this.audioSubtitle = `Lỗi: ${err.message}`;
      this.notify();
    }
  }

  onPlaybackFinished(durationSec) {
    if (this.currentPoi) {
      geofenceEngine.markPlaybackCompleted(this.currentPoi._id);
      analyticsOutbox.recordEvent("audio_completed", this.currentPoi._id, {
        playback_id: this.playbackId,
        total_duration_ms: Math.round(durationSec * 1000),
        listened_ms: this.listenedMs + (Date.now() - this.playStartTime),
      });
    }

    this.cleanup();
    this.state = NarrationState.IDLE;
    this.notify();
  }

  async togglePlayPause() {
    if (this.player && typeof this.player.play === "function") {
      try {
        if (this.state === NarrationState.PLAYING) {
          this.player.pause();
          this.listenedMs += Date.now() - this.playStartTime;
          this.state = NarrationState.PAUSED;
          this.notify();
        } else if (this.state === NarrationState.PAUSED) {
          this.player.play();
          this.playStartTime = Date.now();
          this.state = NarrationState.PLAYING;
          this.notify();
        }
      } catch (err) {
        console.warn("[NarrationController] togglePlayPause error:", err.message);
      }
    } else {
      // Toggle for simulation mode
      if (this.state === NarrationState.PLAYING) {
        this.state = NarrationState.PAUSED;
        if (this.simulationTimer) clearTimeout(this.simulationTimer);
        this.notify();
      } else if (this.state === NarrationState.PAUSED) {
        this.state = NarrationState.PLAYING;
        this.simulationTimer = setTimeout(() => this.onPlaybackFinished(10), 10000);
        this.notify();
      }
    }
  }

  async stop(userInitiated = false) {
    if (this.simulationTimer) {
      clearTimeout(this.simulationTimer);
      this.simulationTimer = null;
    }

    if (this.statusSubscription && typeof this.statusSubscription.remove === "function") {
      this.statusSubscription.remove();
      this.statusSubscription = null;
    }

    if (this.player) {
      try {
        if (this.state === NarrationState.PLAYING) {
          this.listenedMs += Date.now() - this.playStartTime;
        }
        if (typeof this.player.pause === "function") this.player.pause();
        if (typeof this.player.release === "function") this.player.release();
      } catch (e) {}
      this.player = null;
    }

    if (userInitiated && this.currentPoi) {
      geofenceEngine.suppressCurrentZone(this.currentPoi._id);
    }

    this.cleanup();
    this.state = NarrationState.IDLE;
    this.notify();
  }

  cleanup() {
    if (this.simulationTimer) {
      clearTimeout(this.simulationTimer);
      this.simulationTimer = null;
    }
    if (this.statusSubscription && typeof this.statusSubscription.remove === "function") {
      this.statusSubscription.remove();
      this.statusSubscription = null;
    }
    if (this.player) {
      try {
        if (typeof this.player.release === "function") this.player.release();
      } catch (e) {}
      this.player = null;
    }
    this.currentPoi = null;
    this.audioTitle = "";
    this.audioSubtitle = "";
  }
}

export const narrationController = new NarrationController();
