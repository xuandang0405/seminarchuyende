import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Modal,
  ActivityIndicator,
  Alert,
} from "react-native";
import { api } from "../services/api";

export default function RoutePlanningModal({
  visible,
  onClose,
  pois = [],
  userLocation,
  initialOriginPoi = null,
  initialDestinationPoi = null,
  currentLang = "vi",
  onStartRoute,
}) {
  const [originType, setOriginType] = useState("gps"); // "gps" | "poi"
  const [originPoiId, setOriginPoiId] = useState("");
  const [destPoiId, setDestPoiId] = useState("");
  const [travelMode, setTravelMode] = useState("walking"); // "walking" | "driving" | "cycling"
  const [loading, setLoading] = useState(false);
  const [previewRoute, setPreviewRoute] = useState(null);

  useEffect(() => {
    if (visible) {
      if (initialOriginPoi) {
        setOriginType("poi");
        setOriginPoiId(initialOriginPoi._id || initialOriginPoi.id || "");
      } else {
        setOriginType("gps");
        setOriginPoiId("");
      }

      if (initialDestinationPoi) {
        setDestPoiId(initialDestinationPoi._id || initialDestinationPoi.id || "");
      } else if (pois.length > 0 && !destPoiId) {
        setDestPoiId(pois[0]._id || pois[0].id || "");
      }
      setPreviewRoute(null);
    }
  }, [visible, initialOriginPoi, initialDestinationPoi, pois]);

  const handleCalculateRoute = async () => {
    if (originType === "gps" && !userLocation) {
      Alert.alert("Chưa có GPS", "Vui lòng chờ định vị hoặc chọn điểm xuất phát từ danh sách POI.");
      return;
    }
    if (originType === "poi" && !originPoiId) {
      Alert.alert("Thiếu điểm xuất phát", "Vui lòng chọn địa điểm POI xuất phát.");
      return;
    }
    if (!destPoiId) {
      Alert.alert("Thiếu điểm đến", "Vui lòng chọn địa điểm POI đích đến.");
      return;
    }
    if (originType === "poi" && originPoiId === destPoiId) {
      Alert.alert("Điểm trùng nhau", "Điểm xuất phát và điểm đến không được trùng nhau.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        mode: travelMode,
        locale: currentLang,
      };

      if (originType === "gps") {
        payload.origin = {
          latitude: userLocation.latitude,
          longitude: userLocation.longitude,
        };
      } else {
        payload.originPoiId = originPoiId;
      }
      payload.destinationPoiId = destPoiId;

      const data = await api.getRoutePreview(payload);
      setPreviewRoute(data);
    } catch (err) {
      Alert.alert("Không thể tìm đường", err.message || "Vui lòng thử lại sau.");
    } finally {
      setLoading(false);
    }
  };

  const handleStart = () => {
    if (!previewRoute) return;
    const destPoi = pois.find((p) => (p._id || p.id) === destPoiId);
    const originPoi = originType === "poi" ? pois.find((p) => (p._id || p.id) === originPoiId) : null;
    
    if (onStartRoute) {
      onStartRoute({
        route: previewRoute,
        destinationPoi: destPoi,
        originPoi,
        mode: travelMode,
      });
    }
    onClose();
  };

  const handleSwap = () => {
    if (originType === "poi") {
      const prevOrigin = originPoiId;
      setOriginPoiId(destPoiId);
      setDestPoiId(prevOrigin);
      setPreviewRoute(null);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>🧭 Tìm Đường Đi OSRM</Text>
            <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
              <Text style={styles.closeText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.content}>
            {/* Origin Selection */}
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>📍 Điểm xuất phát (Điểm A):</Text>
              <View style={styles.typeSelector}>
                <TouchableOpacity
                  style={[styles.typeBtn, originType === "gps" && styles.typeBtnActive]}
                  onPress={() => {
                    setOriginType("gps");
                    setPreviewRoute(null);
                  }}
                >
                  <Text style={[styles.typeBtnText, originType === "gps" && styles.typeBtnTextActive]}>
                    Vị trí GPS của tôi
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.typeBtn, originType === "poi" && styles.typeBtnActive]}
                  onPress={() => {
                    setOriginType("poi");
                    if (!originPoiId && pois.length > 0) setOriginPoiId(pois[0]._id || pois[0].id);
                    setPreviewRoute(null);
                  }}
                >
                  <Text style={[styles.typeBtnText, originType === "poi" && styles.typeBtnTextActive]}>
                    Chọn từ POI
                  </Text>
                </TouchableOpacity>
              </View>

              {originType === "poi" && (
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.poiPicker}>
                  {pois.map((p) => {
                    const id = p._id || p.id;
                    const isSelected = originPoiId === id;
                    return (
                      <TouchableOpacity
                        key={`orig-${id}`}
                        style={[styles.poiChip, isSelected && styles.poiChipActive]}
                        onPress={() => {
                          setOriginPoiId(id);
                          setPreviewRoute(null);
                        }}
                      >
                        <Text style={[styles.poiChipText, isSelected && styles.poiChipTextActive]}>
                          {p.name}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </ScrollView>
              )}
            </View>

            {/* Swap Button if POI to POI */}
            {originType === "poi" && (
              <TouchableOpacity style={styles.swapBtn} onPress={handleSwap}>
                <Text style={styles.swapText}>⇅ Hoán đổi điểm A ↔ B</Text>
              </TouchableOpacity>
            )}

            {/* Destination Selection */}
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>🏁 Điểm đến (Điểm B):</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.poiPicker}>
                {pois.map((p) => {
                  const id = p._id || p.id;
                  const isSelected = destPoiId === id;
                  return (
                    <TouchableOpacity
                      key={`dest-${id}`}
                      style={[styles.poiChip, isSelected && styles.poiChipActiveDest]}
                      onPress={() => {
                        setDestPoiId(id);
                        setPreviewRoute(null);
                      }}
                    >
                      <Text style={[styles.poiChipText, isSelected && styles.poiChipTextActive]}>
                        {p.name}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>
            </View>

            {/* Travel Mode */}
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>Phương tiện di chuyển:</Text>
              <View style={styles.typeSelector}>
                <TouchableOpacity
                  style={[styles.typeBtn, travelMode === "walking" && styles.typeBtnActive]}
                  onPress={() => {
                    setTravelMode("walking");
                    setPreviewRoute(null);
                  }}
                >
                  <Text style={[styles.typeBtnText, travelMode === "walking" && styles.typeBtnTextActive]}>
                    🚶 Đi bộ
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.typeBtn, travelMode === "driving" && styles.typeBtnActive]}
                  onPress={() => {
                    setTravelMode("driving");
                    setPreviewRoute(null);
                  }}
                >
                  <Text style={[styles.typeBtnText, travelMode === "driving" && styles.typeBtnTextActive]}>
                    🏍️ Xe máy/Ô tô
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.typeBtn, travelMode === "cycling" && styles.typeBtnActive]}
                  onPress={() => {
                    setTravelMode("cycling");
                    setPreviewRoute(null);
                  }}
                >
                  <Text style={[styles.typeBtnText, travelMode === "cycling" && styles.typeBtnTextActive]}>
                    🚲 Xe đạp
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* Action Calculate */}
            <TouchableOpacity
              style={[styles.actionBtn, loading && { opacity: 0.7 }]}
              onPress={handleCalculateRoute}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.actionBtnText}>🔍 Xem Trước Tuyến Đường</Text>
              )}
            </TouchableOpacity>

            {/* Route Preview Details */}
            {previewRoute && (
              <View style={styles.resultBox}>
                <View style={styles.metricsRow}>
                  <View style={styles.metricItem}>
                    <Text style={styles.metricLabel}>Khoảng cách</Text>
                    <Text style={styles.metricValue}>
                      {previewRoute.route_distance_m >= 1000
                        ? (previewRoute.route_distance_m / 1000).toFixed(1) + " km"
                        : Math.round(previewRoute.route_distance_m) + " m"}
                    </Text>
                  </View>
                  <View style={styles.metricDivider} />
                  <View style={styles.metricItem}>
                    <Text style={styles.metricLabel}>Thời gian ước tính</Text>
                    <Text style={styles.metricValue}>
                      ~{Math.ceil(previewRoute.route_duration_s / 60)} phút
                    </Text>
                  </View>
                </View>

                {/* Steps Preview */}
                {previewRoute.legs?.[0]?.steps?.length > 0 && (
                  <View style={styles.stepsPreview}>
                    <Text style={styles.stepsTitle}>Chỉ dẫn các bước:</Text>
                    {previewRoute.legs[0].steps.slice(0, 4).map((step, idx) => (
                      <Text key={idx} style={styles.stepItemText} numberOfLines={2}>
                        {idx + 1}. {step.instruction} ({Math.round(step.distance_m)}m)
                      </Text>
                    ))}
                    {previewRoute.legs[0].steps.length > 4 && (
                      <Text style={styles.stepMoreText}>
                        + {previewRoute.legs[0].steps.length - 4} bước tiếp theo khi di chuyển...
                      </Text>
                    )}
                  </View>
                )}

                <TouchableOpacity style={styles.startNavBtn} onPress={handleStart}>
                  <Text style={styles.startNavBtnText}>🚀 Bắt Đầu Chỉ Đường Trực Tiếp</Text>
                </TouchableOpacity>
              </View>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: "#ffffff",
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: "85%",
    paddingBottom: 24,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#f1f5f9",
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#0f172a",
  },
  closeBtn: {
    padding: 6,
  },
  closeText: {
    fontSize: 20,
    color: "#64748b",
  },
  content: {
    padding: 20,
  },
  section: {
    marginBottom: 16,
  },
  sectionLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#334155",
    marginBottom: 8,
  },
  typeSelector: {
    flexDirection: "row",
    gap: 8,
  },
  typeBtn: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: "#f1f5f9",
    alignItems: "center",
  },
  typeBtnActive: {
    backgroundColor: "#ff6b35",
  },
  typeBtnText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#475569",
  },
  typeBtnTextActive: {
    color: "#ffffff",
  },
  poiPicker: {
    marginTop: 8,
    flexDirection: "row",
  },
  poiChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: "#e2e8f0",
    marginRight: 8,
  },
  poiChipActive: {
    backgroundColor: "#0284c7",
  },
  poiChipActiveDest: {
    backgroundColor: "#16a34a",
  },
  poiChipText: {
    fontSize: 12,
    fontWeight: "500",
    color: "#334155",
  },
  poiChipTextActive: {
    color: "#ffffff",
    fontWeight: "700",
  },
  swapBtn: {
    alignSelf: "center",
    paddingVertical: 4,
    paddingHorizontal: 12,
    backgroundColor: "#f8fafc",
    borderWidth: 1,
    borderColor: "#e2e8f0",
    borderRadius: 16,
    marginBottom: 14,
  },
  swapText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#64748b",
  },
  actionBtn: {
    backgroundColor: "#0f172a",
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 4,
  },
  actionBtnText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "700",
  },
  resultBox: {
    marginTop: 16,
    padding: 16,
    backgroundColor: "#f8fafc",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  metricsRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    marginBottom: 12,
  },
  metricItem: {
    alignItems: "center",
  },
  metricLabel: {
    fontSize: 12,
    color: "#64748b",
  },
  metricValue: {
    fontSize: 18,
    fontWeight: "800",
    color: "#ff6b35",
    marginTop: 2,
  },
  metricDivider: {
    width: 1,
    height: 28,
    backgroundColor: "#cbd5e1",
  },
  stepsPreview: {
    marginTop: 8,
    borderTopWidth: 1,
    borderTopColor: "#e2e8f0",
    paddingTop: 10,
  },
  stepsTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: "#334155",
    marginBottom: 6,
  },
  stepItemText: {
    fontSize: 12,
    color: "#475569",
    marginBottom: 4,
  },
  stepMoreText: {
    fontSize: 11,
    color: "#94a3b8",
    fontStyle: "italic",
    marginTop: 2,
  },
  startNavBtn: {
    backgroundColor: "#16a34a",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 14,
  },
  startNavBtnText: {
    color: "#ffffff",
    fontSize: 14,
    fontWeight: "700",
  },
});
