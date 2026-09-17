import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { offlinePackService } from "../services/OfflinePackService";

export default function OfflineScreen({ onBack }) {
  const [loading, setLoading] = useState(false);
  const [progressStatus, setProgressStatus] = useState("");
  const [manifest, setManifest] = useState(null);

  useEffect(() => {
    loadManifest();
  }, []);

  const loadManifest = async () => {
    const data = await offlinePackService.getActiveManifest();
    setManifest(data);
  };

  const handleDownload = async () => {
    if (!session || session.type !== "user" || !session.userToken) {
      Alert.alert(
        "Yêu Cầu Quyền Sở Hữu",
        "Chỉ tài khoản du khách đã thanh toán mua tour mới được phép tải trọn gói ngoại tuyến (BR-ACCESS-05). Vui lòng đăng nhập tài khoản của bạn."
      );
      return;
    }

    setLoading(true);
    setProgressStatus("Đang kiểm tra quyền sở hữu và khởi tạo tải dữ liệu...");

    try {
      const result = await offlinePackService.downloadDistrict4Pack((p) => {
        if (p.status === "fetching_metadata") setProgressStatus("1/4: Đang tải danh sách POI & Thuyết minh...");
        if (p.status === "fetching_tours") setProgressStatus("2/4: Đang tải tuyến đường du lịch...");
        if (p.status === "staging") setProgressStatus("3/4: Đang kiểm tra toàn vẹn dữ liệu...");
        if (p.status === "saving") setProgressStatus("4/4: Đang lưu vào bộ nhớ ngoại tuyến...");
      });

      setManifest(result);
      Alert.alert("Thành Công", "Đã xác thực bản quyền và lưu trữ toàn bộ gói dữ liệu Quận 4 vào bộ nhớ máy (Hiệu lực 7 ngày)!");
    } catch (err) {
      Alert.alert("Lỗi tải gói", err.message || "Không thể tải gói ngoại tuyến");
    } finally {
      setLoading(false);
      setProgressStatus("");
    }
  };

  const handleDelete = async () => {
    Alert.alert("Xác nhận xóa", "Bạn có chắc chắn muốn xóa gói ngoại tuyến khỏi bộ nhớ máy?", [
      { text: "Hủy", style: "cancel" },
      {
        text: "Xóa",
        style: "destructive",
        onPress: async () => {
          await offlinePackService.removePack();
          setManifest(null);
        },
      },
    ]);
  };

  return (
    <View style={styles.container}>
      {/* Top Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Text style={styles.backBtnText}>← Quay Lại Bản Đồ</Text>
        </TouchableOpacity>
        <Text style={styles.title}>📦 Dữ Liệu Ngoại Tuyến (Offline)</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Gói Dữ Liệu Du Lịch Quận 4</Text>
          <Text style={styles.cardDesc}>
            Tải trước tọa độ Geofence, kịch bản thuyết minh và lộ trình tour. Khi đi vào các ngõ hẻm
            hoặc khu vực mất sóng 4G/Wifi, ứng dụng vẫn tự động nhận diện vị trí và phát thuyết minh bình thường (Use Case F01/F06).
          </Text>

          {manifest ? (
            <View style={styles.statusBox}>
              <View style={styles.badgeActive}>
                <Text style={styles.badgeActiveText}>✅ ĐÃ SẴN SÀNG NGOẠI TUYẾN</Text>
              </View>

              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Phiên bản gói:</Text>
                <Text style={styles.metaValue}>v{manifest.version} ({manifest.pack_id})</Text>
              </View>
              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Số điểm di tích/ẩm thực:</Text>
                <Text style={styles.metaValue}>{manifest.pois_count} địa điểm</Text>
              </View>
              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Số tuyến tour đi bộ:</Text>
                <Text style={styles.metaValue}>{manifest.tours_count} tuyến</Text>
              </View>
              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Dung lượng chiếm dụng:</Text>
                <Text style={styles.metaValue}>{(manifest.total_bytes / 1024).toFixed(1)} KB</Text>
              </View>
              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Cập nhật lần cuối:</Text>
                <Text style={styles.metaValue}>
                  {new Date(manifest.published_at).toLocaleTimeString("vi-VN")} - {new Date(manifest.published_at).toLocaleDateString("vi-VN")}
                </Text>
              </View>

              <View style={styles.btnRow}>
                <TouchableOpacity style={styles.repairBtn} onPress={handleDownload} disabled={loading}>
                  <Text style={styles.repairBtnText}>🔄 Cập Nhật / Đồng Bộ Lại</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.deleteBtn} onPress={handleDelete}>
                  <Text style={styles.deleteBtnText}>🗑️ Xóa Gói</Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : (
            <View style={{ gap: 12 }}>
              {loading && (
                <View style={styles.loadingBox}>
                  <ActivityIndicator color="#ff6b35" />
                  <Text style={styles.loadingText}>{progressStatus}</Text>
                </View>
              )}

              <TouchableOpacity
                style={styles.downloadBtn}
                onPress={handleDownload}
                disabled={loading}
              >
                <Text style={styles.downloadBtnText}>
                  {loading ? "Đang tải gói..." : "⬇ Tải Gói Dữ Liệu Quận 4 Về Máy"}
                </Text>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* Cached POIs preview if manifest is present */}
        {manifest && manifest.pois && (
          <View style={styles.previewSection}>
            <Text style={styles.previewTitle}>Danh Sách Địa Điểm Đã Lưu Ngoại Tuyến</Text>
            {manifest.pois.map((poi) => (
              <View key={poi._id} style={styles.poiItem}>
                <Text style={styles.poiName}>{poi.name}</Text>
                <Text style={styles.poiAddress}>📍 {poi.address}</Text>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    paddingTop: 50,
  },
  header: {
    paddingHorizontal: 20,
    marginBottom: 16,
  },
  backBtn: {
    alignSelf: "flex-start",
    backgroundColor: "#1e293b",
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    marginBottom: 12,
  },
  backBtnText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },
  title: {
    fontSize: 22,
    fontWeight: "800",
    color: "#fff",
  },
  scroll: {
    paddingHorizontal: 20,
    paddingBottom: 40,
    gap: 20,
  },
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#ff6b35",
    marginBottom: 8,
  },
  cardDesc: {
    fontSize: 13,
    color: "#94a3b8",
    lineHeight: 20,
    marginBottom: 16,
  },
  downloadBtn: {
    backgroundColor: "#ff6b35",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  downloadBtnText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 15,
  },
  loadingBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 12,
    backgroundColor: "rgba(255, 107, 53, 0.1)",
    borderRadius: 8,
  },
  loadingText: {
    color: "#ff6b35",
    fontSize: 13,
    fontWeight: "600",
  },
  statusBox: {
    backgroundColor: "#0f172a",
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  badgeActive: {
    backgroundColor: "rgba(16, 185, 129, 0.15)",
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6,
    alignSelf: "flex-start",
    marginBottom: 6,
  },
  badgeActiveText: {
    color: "#10b981",
    fontWeight: "800",
    fontSize: 12,
  },
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  metaLabel: {
    color: "#94a3b8",
    fontSize: 13,
  },
  metaValue: {
    color: "#ffffff",
    fontSize: 13,
    fontWeight: "600",
  },
  btnRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 12,
  },
  repairBtn: {
    flex: 1,
    backgroundColor: "#334155",
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: "center",
  },
  repairBtnText: {
    color: "#cbd5e1",
    fontWeight: "600",
    fontSize: 12,
  },
  deleteBtn: {
    backgroundColor: "rgba(239, 68, 68, 0.15)",
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 8,
    alignItems: "center",
  },
  deleteBtnText: {
    color: "#ef4444",
    fontWeight: "700",
    fontSize: 12,
  },
  previewSection: {
    gap: 10,
  },
  previewTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#ffffff",
  },
  poiItem: {
    backgroundColor: "#1e293b",
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  poiName: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 14,
  },
  poiAddress: {
    color: "#94a3b8",
    fontSize: 12,
    marginTop: 2,
  },
});
