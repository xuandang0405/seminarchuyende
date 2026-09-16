import { Platform } from "react-native";

// Base URL for API requests.
// On real Android devices, replace "10.0.2.2" with your development machine's LAN IP address.
export const API_BASE_URL = Platform.select({
  android: "http://10.0.2.2:8000/api/v1",
  ios: "http://localhost:8000/api/v1",
  default: "http://localhost:8000/api/v1",
});

export const BACKEND_ROOT = Platform.select({
  android: "http://10.0.2.2:8000",
  ios: "http://localhost:8000",
  default: "http://localhost:8000",
});

export const api = {
  API_BASE_URL,
  BACKEND_ROOT,

  /**
   * Helper to normalize audio and image URLs that might be relative paths (e.g. "/storage/...")
   */
  resolveUrl(url) {
    if (!url) return null;
    if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("file://")) {
      return url;
    }
    return `${BACKEND_ROOT}${url.startsWith("/") ? "" : "/"}${url}`;
  },

  /**
   * GET /api/v1/pois - Fetch public active POIs with localized name & description.
   */
  async getPOIs({ lang = "vi", category = null, search = null, limit = 50 } = {}) {
    try {
      const params = new URLSearchParams({ lang, limit: String(limit) });
      if (category) params.append("category", category);
      if (search) params.append("search", search);

      const res = await fetch(`${API_BASE_URL}/pois?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return (data || []).map((poi) => ({
        ...poi,
        audio_url: this.resolveUrl(poi.audio_url),
        images: (poi.images || []).map((img) => this.resolveUrl(img)),
      }));
    } catch (err) {
      console.warn("[API] getPOIs error:", err.message);
      return [];
    }
  },

  /**
   * GET /api/v1/pois/nearby - Geospatial 2dsphere search.
   */
  async getNearbyPOIs({ lat, lng, radius_meters = 500, lang = "vi" }) {
    try {
      const params = new URLSearchParams({
        lat: String(lat),
        lng: String(lng),
        radius_meters: String(radius_meters),
        lang,
      });
      const res = await fetch(`${API_BASE_URL}/pois/nearby?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return (data || []).map((poi) => ({
        ...poi,
        audio_url: this.resolveUrl(poi.audio_url),
      }));
    } catch (err) {
      console.warn("[API] getNearbyPOIs error:", err.message);
      return [];
    }
  },

  /**
   * GET /api/v1/pois/{id} - Get single POI with fallback details.
   */
  async getPOIDetail(poiId, lang = "vi") {
    try {
      const res = await fetch(`${API_BASE_URL}/pois/${poiId}?lang=${lang}`);
      if (!res.ok) return null;
      const poi = await res.json();
      return {
        ...poi,
        audio_url: this.resolveUrl(poi.audio_url),
        images: (poi.images || []).map((img) => this.resolveUrl(img)),
      };
    } catch (err) {
      console.warn("[API] getPOIDetail error:", err.message);
      return null;
    }
  },

  /**
   * GET /api/v1/pois/{id}/menu - Get food & beverage menu for culinary POIs.
   */
  async getPOIMenu(poiId) {
    try {
      const res = await fetch(`${API_BASE_URL}/pois/${poiId}/menu`);
      if (!res.ok) return [];
      const items = await res.json();
      return (items || []).map((item) => ({
        ...item,
        image_url: this.resolveUrl(item.image_url),
      }));
    } catch (err) {
      console.warn("[API] getPOIMenu error:", err.message);
      return [];
    }
  },

  /**
   * GET /api/v1/qr/{code} - Resolve scanned QR code to target POI.
   */
  async resolveQR(code, lang = "vi") {
    try {
      const res = await fetch(`${API_BASE_URL}/qr/${encodeURIComponent(code)}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        return { valid: false, error: errData.detail || "Mã QR không hợp lệ hoặc đã hết hạn" };
      }
      const data = await res.json();
      if (data.poi) {
        data.poi.audio_url = this.resolveUrl(data.poi.audio_url);
      }
      return data;
    } catch (err) {
      console.warn("[API] resolveQR error:", err.message);
      return { valid: false, error: "Lỗi kết nối máy chủ" };
    }
  },

  /**
   * GET /api/v1/tours - Fetch walking tour routes in District 4.
   */
  async getTours() {
    try {
      const res = await fetch(`${API_BASE_URL}/tours`);
      if (!res.ok) return [];
      return await res.json();
    } catch (err) {
      console.warn("[API] getTours error:", err.message);
      return [];
    }
  },

  /**
   * GET /api/v1/tours/{id} - Fetch tour details with sequenced stops.
   */
  async getTourDetail(tourId) {
    try {
      const res = await fetch(`${API_BASE_URL}/tours/${tourId}`);
      if (!res.ok) return null;
      return await res.json();
    } catch (err) {
      console.warn("[API] getTourDetail error:", err.message);
      return null;
    }
  },

  /**
   * POST /api/v1/analytics/events/batch - Flush outbox analytics events with per-event ACK.
   */
  async sendAnalyticsBatch(events) {
    try {
      const res = await fetch(`${API_BASE_URL}/analytics/events/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("[API] sendAnalyticsBatch error:", err.message);
      return { success: false, error: err.message };
    }
  },
};
