import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Modal,
  ActivityIndicator,
} from "react-native";
import { api } from "../services/api";
import { tourSessionService } from "../services/TourSessionService";

export default function TourModal({ visible, onClose, onSelectTour }) {
  const [tours, setTours] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTour, setActiveTour] = useState(null);

  useEffect(() => {
    if (visible) {
      loadTours();
      setActiveTour(tourSessionService.getActiveTour());
    }
  }, [visible]);

  const loadTours = async () => {
    setLoading(true);
    const data = await api.getTours();
    setTours(data);
    setLoading(false);
  };

  const handleStartTour = async (tour) => {
    await tourSessionService.startTour(tour);
    setActiveTour(tour);
    if (onSelectTour) onSelectTour(tour);
    onClose();
  };

  const handleEndTour = async () => {
    await tourSessionService.endTour();
    setActiveTour(null);
    if (onSelectTour) onSelectTour(null);
    onClose();
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>🚶 Tuyến Đi Bộ Thuyết Minh (Tours)</Text>
            <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
              <Text style={styles.closeText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.content}>
            {loading ? (
              <ActivityIndicator color="#ff6b35" style={{ padding: 20 }} />
            ) : tours.length === 0 ? (
              <View style={styles.empty}>
                <Text style={styles.emptyText}>Chưa có tuyến du lịch nào</Text>
              </View>
            ) : (
              tours.map((tour) => {
                const isActive = activeTour && activeTour._id === tour._id;
                return (
                  <View key={tour._id} style={[styles.tourCard, isActive && styles.tourCardActive]}>
                    <View style={styles.tourHeader}>
                      <Text style={styles.tourName}>{tour.name}</Text>
                      <View style={styles.stopsBadge}>
                        <Text style={styles.stopsText}>
                          {(tour.poi_ids || []).length} điểm dừng
                        </Text>
                      </View>
                    </View>

                    <Text style={styles.tourDesc}>{tour.description}</Text>

                    <View style={styles.actionRow}>
                      {isActive ? (
                        <TouchableOpacity style={styles.endBtn} onPress={handleEndTour}>
                          <Text style={styles.endBtnText}>Kết Thúc Tuyến Đang Đi</Text>
                        </TouchableOpacity>
                      ) : (
                        <TouchableOpacity
                          style={styles.startBtn}
                          onPress={() => handleStartTour(tour)}
                        >
                          <Text style={styles.startBtnText}>Bắt Đầu Tuyến Này</Text>
                        </TouchableOpacity>
                      )}
                    </View>
                  </View>
                );
              })
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
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: "#0f172a",
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: "80%",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  header: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.08)",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: "800",
    color: "#ffffff",
  },
  closeBtn: {
    padding: 6,
  },
  closeText: {
    color: "#94a3b8",
    fontSize: 18,
    fontWeight: "bold",
  },
  content: {
    padding: 20,
    gap: 16,
  },
  tourCard: {
    backgroundColor: "#1e293b",
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  tourCardActive: {
    borderColor: "#ff6b35",
    backgroundColor: "rgba(255,107,53,0.08)",
  },
  tourHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
    gap: 10,
  },
  tourName: {
    fontSize: 16,
    fontWeight: "800",
    color: "#ffffff",
    flex: 1,
  },
  stopsBadge: {
    backgroundColor: "rgba(0, 180, 216, 0.2)",
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  stopsText: {
    color: "#00b4d8",
    fontSize: 11,
    fontWeight: "700",
  },
  tourDesc: {
    fontSize: 13,
    color: "#94a3b8",
    lineHeight: 18,
    marginBottom: 14,
  },
  actionRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
  },
  startBtn: {
    backgroundColor: "#ff6b35",
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  startBtnText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 13,
  },
  endBtn: {
    backgroundColor: "#ef4444",
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  endBtnText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 13,
  },
  empty: {
    padding: 30,
    alignItems: "center",
  },
  emptyText: {
    color: "#64748b",
    fontSize: 14,
  },
});
