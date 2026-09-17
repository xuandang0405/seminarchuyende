import { Audio } from "expo-av";
import { geofenceEngine } from "./GeofenceEngine";
import { audioSourceResolver } from "./AudioSourceResolver";
import { analyticsOutbox } from "./AnalyticsOutbox";
import { api } from "./api";

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
    this.sound = null;
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
  }

  setSession(userToken, guestToken, tourId = null) {
    this.userToken = userToken;
    this.guestToken = guestToken;
    if (tourId) this.activeTourId = tourId;
  }

  subscribe(listener) {
    this.listeners.add(listener);
    // Immediately emit current state to new subscriber
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
      activeTourId: this.activeTourId
    };
  }

  async ensureAudioMode() {
    if (this.configuredAudioMode) return;
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
        staysActiveInBackground: true,
        shouldDuckAndroid: true,
      });
      this.configuredAudioMode = true;
    } catch (e) {
      console.warn("[NarrationController] setAudioModeAsync error:", e.message);
    }
  }

  /**
   * Main request method to play narration.
   * Enforces priority: "manual" or "qr" preempts "gps".
   * Active "manual" playback cannot be interrupted by "gps".
   * Gated by backend AccessService via playback grant.
   */
  async requestNarration(poi, triggerType = "manual", lang = "vi", userConsentTrial = false) {
    if (!poi) return;

    // Invariant: GPS cannot interrupt active manual playback
    if (
      triggerType === "gps" &&
      this.triggerType !== "gps" &&
      (this.state === NarrationState.PLAYING || this.state === NarrationState.LOADING)
    ) {
      return;
    }

    // If same POI is already playing, do not restart
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

      // Resolve audio source (local offline -> remote URL -> fallback)
      const source = await audioSourceResolver.resolveAudioSource(poi, lang);
      if (!source || !source.uri) {
        throw new Error("Không tìm thấy tệp thuyết minh âm thanh cho địa điểm này");
      }

      let playbackUri = source.uri;

      // If source is remote HTTP, check backend playback grant
      if (source.sourceType === "remote" && playbackUri.startsWith("http")) {
        const tourId = this.activeTourId || poi.tour_id || "tour_district_4_culinary_history";
        const grantRes = await api.requestPlaybackGrant({
          tourId,
          poiId: poi._id,
          language: lang,
          triggerType,
          userConsentTrial
        }, this.guestToken, this.userToken);

        if (!grantRes.ok || !grantRes.data.granted) {
          const errorCode = grantRes.data.error_code || "TOUR_PURCHASE_REQUIRED";
          this.lastErrorCode = errorCode;
          this.state = NarrationState.ERROR;

          if (errorCode === "TRIAL_CONSENT_REQUIRED") {
            this.audioSubtitle = "💡 Bạn còn 1 lượt nghe thử miễn phí. Bấm Xác Nhận để nghe thuyết minh.";
          } else {
            this.audioSubtitle = "🔒 Đã hết lượt nghe thử. Vui lòng mua tour để mở khóa toàn bộ nội dung thuyết minh.";
          }
          this.notify();
          return;
        }

        const grantToken = grantRes.data.grant_token;
        if (grantToken) {
          const delim = playbackUri.includes("?") ? "&" : "?";
          playbackUri = `${playbackUri}${delim}grant_token=${grantToken}`;
        }
      }

      const { sound } = await Audio.Sound.createAsync(
        { uri: playbackUri },
        { shouldPlay: true },
        this.onPlaybackStatusUpdate.bind(this)
      );

      this.sound = sound;
      this.state = NarrationState.PLAYING;
      this.playStartTime = Date.now();
      this.notify();

      // Record analytics event
      analyticsOutbox.recordEvent("audio_play", poi._id, {
        playback_id: this.playbackId,
        trigger_type: triggerType,
        lang,
        source_type: source.sourceType,
      });
    } catch (err) {
      console.warn("[NarrationController] Playback error:", err.message);
      this.state = NarrationState.ERROR;
      this.audioSubtitle = `Lỗi: ${err.message}`;
      this.notify();
    }
  }

  onPlaybackStatusUpdate(status) {
    if (!status.isLoaded) {
      if (status.error) {
        this.state = NarrationState.ERROR;
        this.notify();
      }
      return;
    }

    if (status.didJustFinish) {
      // Audio playback finished successfully!
      if (this.currentPoi) {
        // Apply cooldown now (SD04 / AD16)
        geofenceEngine.markPlaybackCompleted(this.currentPoi._id);
        
        analyticsOutbox.recordEvent("audio_completed", this.currentPoi._id, {
          playback_id: this.playbackId,
          total_duration_ms: status.durationMillis,
          listened_ms: this.listenedMs + (status.positionMillis || 0),
        });
      }

      this.cleanup();
      this.state = NarrationState.IDLE;
      this.notify();
    }
  }

  async togglePlayPause() {
    if (!this.sound) return;

    try {
      if (this.state === NarrationState.PLAYING) {
        await this.sound.pauseAsync();
        this.listenedMs += Date.now() - this.playStartTime;
        this.state = NarrationState.PAUSED;
        this.notify();
      } else if (this.state === NarrationState.PAUSED) {
        await this.sound.playAsync();
        this.playStartTime = Date.now();
        this.state = NarrationState.PLAYING;
        this.notify();
      }
    } catch (err) {
      console.warn("[NarrationController] togglePlayPause error:", err.message);
    }
  }

  /**
   * User explicitly taps Stop. Suppresses auto-play until user leaves zone.
   */
  async stop(userInitiated = false) {
    if (this.sound) {
      try {
        if (this.state === NarrationState.PLAYING) {
          this.listenedMs += Date.now() - this.playStartTime;
        }
        await this.sound.stopAsync();
        await this.sound.unloadAsync();
      } catch (e) {}
      this.sound = null;
    }

    if (userInitiated && this.currentPoi) {
      // Prevent GPS from immediately re-triggering while tourist stays in same spot
      geofenceEngine.suppressCurrentZone(this.currentPoi._id);
    }

    this.cleanup();
    this.state = NarrationState.IDLE;
    this.notify();
  }

  cleanup() {
    if (this.sound) {
      this.sound.unloadAsync().catch(() => {});
      this.sound = null;
    }
    this.currentPoi = null;
    this.audioTitle = "";
    this.audioSubtitle = "";
  }
}

export const narrationController = new NarrationController();
