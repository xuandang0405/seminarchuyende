import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Image,
  Modal,
  ActivityIndicator,
} from "react-native";
import { api } from "../services/api";

export default function POIDetailModal({
  poi,
  visible,
  onClose,
  onPlayAudio,
  onDirections,
  currentLang = "vi",
}) {
  const [menuItems, setMenuItems] = useState([]);
  const [loadingMenu, setLoadingMenu] = useState(false);

  useEffect(() => {
    if (poi && visible) {
      loadMenu();
    }
  }, [poi, visible]);

  const loadMenu = async () => {
    if (!poi) return;
    setLoadingMenu(true);
    const items = await api.getPOIMenu(poi._id);
    setMenuItems(items);
    setLoadingMenu(false);
  };

  if (!poi) return null;

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          {/* Header Bar */}
          <View style={styles.header}>
            <View style={styles.dragPill} />
            <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
              <Text style={styles.closeText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.content}>
            {/* Main Image */}
            {poi.images && poi.images.length > 0 ? (
              <Image source={{ uri: poi.images[0] }} style={styles.coverImage} resizeMode="cover" />
            ) : (
              <View style={[styles.coverImage, styles.placeholderImage]}>
                <Text style={styles.placeholderIcon}>🏛️</Text>
              </View>
            )}

            {/* Title & Category Badge */}
            <View style={styles.titleRow}>
              <Text style={styles.title}>{poi.name}</Text>
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{poi.category || "Điểm đến"}</Text>
              </View>
            </View>

            {/* Address */}
            <Text style={styles.address}>📍 {poi.address || "Quận 4, TP. Hồ Chí Minh"}</Text>

            {/* Fallback warning if content is in fallback language */}
            {poi.is_fallback && (
              <View style={styles.fallbackNotice}>
                <Text style={styles.fallbackText}>
                  ℹ️ Chưa có bản dịch {currentLang.toUpperCase()}, đang hiển thị bằng {poi.resolved_lang?.toUpperCase()}
                </Text>
              </View>
            )}

            {/* Action Play Button */}
            <TouchableOpacity
              style={styles.playButton}
              onPress={() => {
                onClose();
                onPlayAudio(poi, "manual");
              }}
            >
              <Text style={styles.playIcon}>▶</Text>
              <Text style={styles.playButtonText}>Nghe Thuyết Minh Âm Thanh</Text>
            </TouchableOpacity>

            {/* Directions Button */}
            {onDirections ? (
              <TouchableOpacity
                style={[styles.playButton, { backgroundColor: "#0284c7", marginTop: 8 }]}
                onPress={() => {
                  onClose();
                  onDirections(poi);
                }}
              >
                <Text style={styles.playIcon}>🧭</Text>
                <Text style={styles.playButtonText}>Chỉ Đường Thực Tế (OSRM)</Text>
              </TouchableOpacity>
            ) : null}

            {/* Description */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Giới Thiệu</Text>
              <Text style={styles.description}>
                {poi.description || "Chưa có mô tả chi tiết cho địa điểm này."}
              </Text>
            </View>

            {/* Culinary Menu Items */}
            {menuItems.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Món Đặc Sản / Thực Đơn</Text>
                {loadingMenu ? (
                  <ActivityIndicator color="#ff6b35" />
                ) : (
                  <View style={styles.menuGrid}>
                    {menuItems.map((item) => (
                      <View key={item._id} style={styles.menuItem}>
                        {item.image_url ? (
                          <Image
                            source={{ uri: item.image_url }}
                            style={styles.menuImage}
                            resizeMode="cover"
                          />
                        ) : (
                          <View style={[styles.menuImage, styles.placeholderMenu]}>
                            <Text style={{ fontSize: 20 }}>🍲</Text>
                          </View>
                        )}
                        <View style={styles.menuInfo}>
                          <Text style={styles.menuName}>{item.name}</Text>
                          {item.description ? (
                            <Text style={styles.menuDesc} numberOfLines={2}>
                              {item.description}
                            </Text>
                          ) : null}
                          <Text style={styles.menuPrice}>
                            {item.price ? Number(item.price).toLocaleString("vi-VN") : 0}{" "}
                            {item.currency || "VND"}
                          </Text>
                        </View>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            )}

            <View style={{ height: 40 }} />
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
    maxHeight: "85%",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  header: {
    paddingVertical: 12,
    alignItems: "center",
    position: "relative",
  },
  dragPill: {
    width: 40,
    height: 4,
    backgroundColor: "#334155",
    borderRadius: 2,
  },
  closeBtn: {
    position: "absolute",
    right: 20,
    top: 8,
    padding: 6,
  },
  closeText: {
    color: "#94a3b8",
    fontSize: 18,
    fontWeight: "bold",
  },
  content: {
    paddingHorizontal: 20,
    paddingBottom: 24,
  },
  coverImage: {
    width: "100%",
    height: 200,
    borderRadius: 16,
    marginBottom: 16,
  },
  placeholderImage: {
    backgroundColor: "#1e293b",
    justifyContent: "center",
    alignItems: "center",
  },
  placeholderIcon: {
    fontSize: 48,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 6,
    gap: 10,
  },
  title: {
    fontSize: 20,
    fontWeight: "800",
    color: "#ffffff",
    flex: 1,
  },
  badge: {
    backgroundColor: "rgba(255, 107, 53, 0.15)",
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "rgba(255, 107, 53, 0.3)",
  },
  badgeText: {
    color: "#ff6b35",
    fontSize: 11,
    fontWeight: "700",
  },
  address: {
    fontSize: 13,
    color: "#94a3b8",
    marginBottom: 16,
  },
  fallbackNotice: {
    backgroundColor: "rgba(245, 158, 11, 0.15)",
    borderWidth: 1,
    borderColor: "rgba(245, 158, 11, 0.3)",
    padding: 8,
    borderRadius: 8,
    marginBottom: 16,
  },
  fallbackText: {
    color: "#fbbf24",
    fontSize: 12,
  },
  playButton: {
    backgroundColor: "#ff6b35",
    paddingVertical: 14,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    marginBottom: 20,
    shadowColor: "#ff6b35",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  playIcon: {
    fontSize: 16,
    color: "#ffffff",
  },
  playButtonText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 15,
  },
  section: {
    marginTop: 16,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#ffffff",
    marginBottom: 8,
  },
  description: {
    fontSize: 14,
    color: "#cbd5e1",
    lineHeight: 22,
  },
  menuGrid: {
    gap: 12,
    marginTop: 8,
  },
  menuItem: {
    flexDirection: "row",
    backgroundColor: "#1e293b",
    borderRadius: 12,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  menuImage: {
    width: 80,
    height: 80,
  },
  placeholderMenu: {
    backgroundColor: "#334155",
    justifyContent: "center",
    alignItems: "center",
  },
  menuInfo: {
    flex: 1,
    padding: 10,
    justifyContent: "center",
  },
  menuName: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 14,
  },
  menuDesc: {
    color: "#94a3b8",
    fontSize: 12,
    marginTop: 2,
  },
  menuPrice: {
    color: "#10b981",
    fontWeight: "800",
    fontSize: 13,
    marginTop: 4,
  },
});
