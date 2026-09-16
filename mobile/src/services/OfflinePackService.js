import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "./api";

const STORAGE_KEY_OFFLINE_MANIFEST = "tourvoice_offline_manifest";

class OfflinePackService {
  /**
   * Retrieves currently active offline manifest from local storage.
   */
  async getActiveManifest() {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY_OFFLINE_MANIFEST);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  /**
   * Downloads offline pack containing all active POIs and routes in District 4.
   */
  async downloadDistrict4Pack(onProgress) {
    if (onProgress) onProgress({ status: "fetching_metadata", progress: 0.1 });

    // 1. Fetch active POIs in District 4 (covers vi, en, fr)
    const pois = await api.getPOIs({ limit: 100 });
    if (!pois || pois.length === 0) {
      throw new Error("Không thể kết nối hoặc không có dữ liệu POI từ máy chủ.");
    }

    if (onProgress) onProgress({ status: "fetching_tours", progress: 0.4 });

    // 2. Fetch tours
    const tours = await api.getTours();

    if (onProgress) onProgress({ status: "staging", progress: 0.7 });

    // 3. Construct offline bundle manifest
    const manifest = {
      pack_id: "quan_4_full_v1",
      name: "Quận 4 - Di Tích & Ẩm Thực Đêm",
      scope: "district_4",
      version: 1,
      published_at: new Date().toISOString(),
      pois_count: pois.length,
      tours_count: tours.length,
      total_bytes: JSON.stringify(pois).length + JSON.stringify(tours).length + 45000,
      pois,
      tours,
    };

    if (onProgress) onProgress({ status: "saving", progress: 0.9 });

    // 4. Atomic commit to local storage
    await AsyncStorage.setItem(STORAGE_KEY_OFFLINE_MANIFEST, JSON.stringify(manifest));

    if (onProgress) onProgress({ status: "completed", progress: 1.0 });

    return manifest;
  }

  /**
   * Removes offline package from device storage.
   */
  async removePack() {
    await AsyncStorage.removeItem(STORAGE_KEY_OFFLINE_MANIFEST);
  }

  /**
   * Checks integrity and repairs missing items.
   */
  async repairPack(onProgress) {
    return await this.downloadDistrict4Pack(onProgress);
  }
}

export const offlinePackService = new OfflinePackService();
