import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "./api";

class AudioSourceResolver {
  /**
   * Resolves playable audio URI for a given POI and target language.
   * Priority:
   * 1. Offline local storage file/data (if offline pack is active).
   * 2. Remote audio URL directly from POI localization object.
   * 3. Fallback to English, then Vietnamese if requested target language has no audio.
   */
  async resolveAudioSource(poi, targetLang = "vi") {
    if (!poi) return null;

    // 1. Check local offline pack
    try {
      const offlineManifestRaw = await AsyncStorage.getItem("tourvoice_offline_manifest");
      if (offlineManifestRaw) {
        const manifest = JSON.parse(offlineManifestRaw);
        const cachedPoi = (manifest.pois || []).find((p) => p._id === poi._id);
        if (cachedPoi && cachedPoi.audio_url) {
          return {
            uri: cachedPoi.audio_url,
            sourceType: "offline_cache",
            resolvedLang: targetLang,
            isFallback: false,
          };
        }
      }
    } catch (e) {
      console.warn("[AudioSourceResolver] Offline check error:", e.message);
    }

    // 2. Check direct POI audio_url (already resolved by backend with fallback)
    if (poi.audio_url) {
      return {
        uri: poi.audio_url,
        sourceType: "remote_url",
        resolvedLang: poi.resolved_lang || targetLang,
        isFallback: poi.is_fallback || false,
      };
    }

    // 3. If missing, query detail endpoint for targetLang
    const detail = await api.getPOIDetail(poi._id, targetLang);
    if (detail && detail.audio_url) {
      return {
        uri: detail.audio_url,
        sourceType: "remote_url",
        resolvedLang: detail.resolved_lang || targetLang,
        isFallback: detail.is_fallback || false,
      };
    }

    return null;
  }
}

export const audioSourceResolver = new AudioSourceResolver();
