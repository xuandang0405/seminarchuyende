import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";

export default function AudioPlayerBar({
  title,
  subtitle,
  triggerType = "GPS",
  isPlaying,
  isLoading,
  onPlayPause,
  onClose,
}) {
  if (!title) return null;

  return (
    <View style={styles.container}>
      <View style={styles.infoCol}>
        <View style={styles.badgeRow}>
          <Text style={styles.title} numberOfLines={1}>
            {title}
          </Text>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>
              {triggerType === "gps" ? "GPS TỰ ĐỘNG" : (triggerType === "qr" ? "MÃ QR" : "CHỌN TAY")}
            </Text>
          </View>
        </View>
        <Text style={styles.subtitle} numberOfLines={1}>
          {subtitle || "Đang phát kịch bản thuyết minh âm thanh..."}
        </Text>
      </View>

      <View style={styles.controlsRow}>
        <TouchableOpacity style={styles.playBtn} onPress={onPlayPause} disabled={isLoading}>
          {isLoading ? (
            <ActivityIndicator size="small" color="#ffffff" />
          ) : (
            <Text style={styles.playBtnText}>{isPlaying ? "⏸" : "▶"}</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
          <Text style={styles.closeBtnText}>✕</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    bottom: 24,
    left: 16,
    right: 16,
    backgroundColor: "rgba(15, 23, 42, 0.95)",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(255, 107, 53, 0.4)",
    paddingVertical: 12,
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 10,
  },
  infoCol: {
    flex: 1,
    marginRight: 12,
  },
  badgeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  title: {
    fontSize: 15,
    fontWeight: "700",
    color: "#ffffff",
    flexShrink: 1,
  },
  badge: {
    backgroundColor: "#00b4d8",
    paddingVertical: 2,
    paddingHorizontal: 6,
    borderRadius: 4,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: "800",
    color: "#0f172a",
  },
  subtitle: {
    fontSize: 12,
    color: "#94a3b8",
    marginTop: 2,
  },
  controlsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  playBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: "#ff6b35",
    justifyContent: "center",
    alignItems: "center",
  },
  playBtnText: {
    fontSize: 18,
    color: "#ffffff",
    marginLeft: 2,
  },
  closeBtn: {
    padding: 6,
  },
  closeBtnText: {
    fontSize: 16,
    color: "#64748b",
  },
});
