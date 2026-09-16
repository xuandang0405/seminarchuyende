import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Switch,
  Modal,
  ScrollView,
} from "react-native";
import { analyticsOutbox } from "../services/AnalyticsOutbox";

export default function SettingsModal({
  visible,
  onClose,
  currentLang,
  onSelectLang,
}) {
  const [consent, setConsent] = useState(true);

  useEffect(() => {
    if (visible) {
      analyticsOutbox.getConsent().then(setConsent);
    }
  }, [visible]);

  const handleToggleConsent = async (val) => {
    setConsent(val);
    await analyticsOutbox.setConsent(val);
  };

  const languages = [
    { code: "vi", label: "Tiếng Việt", flag: "🇻🇳" },
    { code: "en", label: "English", flag: "🇬🇧" },
    { code: "fr", label: "Français", flag: "🇫🇷" },
  ];

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>⚙️ Cài Đặt Hệ Thống</Text>
            <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
              <Text style={styles.closeText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.content}>
            {/* Language Selection */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Ngôn Ngữ Thuyết Minh & Giao Diện</Text>
              <View style={styles.langRow}>
                {languages.map((l) => (
                  <TouchableOpacity
                    key={l.code}
                    style={[
                      styles.langBtn,
                      currentLang === l.code && styles.langBtnActive,
                    ]}
                    onPress={() => onSelectLang(l.code)}
                  >
                    <Text style={styles.langFlag}>{l.flag}</Text>
                    <Text
                      style={[
                        styles.langText,
                        currentLang === l.code && styles.langTextActive,
                      ]}
                    >
                      {l.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* Privacy & Analytics Consent (F08) */}
            <View style={styles.section}>
              <View style={styles.rowBetween}>
                <View style={{ flex: 1, paddingRight: 10 }}>
                  <Text style={styles.sectionTitle}>Đồng Ý Thu Thập Thống Kê</Text>
                  <Text style={styles.sectionDesc}>
                    Cho phép hệ thống ghi nhận lượt nghe và tuyến đường du lịch dưới dạng ẩn danh
                    để nâng cao chất lượng dịch vụ du lịch Quận 4.
                  </Text>
                </View>
                <Switch
                  value={consent}
                  onValueChange={handleToggleConsent}
                  trackColor={{ false: "#334155", true: "#ff6b35" }}
                  thumbColor={consent ? "#ffffff" : "#94a3b8"}
                />
              </View>
            </View>

            {/* System Info */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Thông Tin Đồ Án</Text>
              <Text style={styles.infoLine}>• Đề tài: Hệ Thống Thuyết Minh Du Lịch Tự Động Đa Ngôn Ngữ</Text>
              <Text style={styles.infoLine}>• Khu vực: Quận 4, TP. Hồ Chí Minh</Text>
              <Text style={styles.infoLine}>• Phiên bản: 1.0.0 (Native Expo Build)</Text>
            </View>
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
    maxHeight: "75%",
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
    fontSize: 18,
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
    gap: 20,
  },
  section: {
    backgroundColor: "#1e293b",
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)",
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#ffffff",
    marginBottom: 6,
  },
  sectionDesc: {
    fontSize: 12,
    color: "#94a3b8",
    lineHeight: 18,
  },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  langRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 8,
  },
  langBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "#0f172a",
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#334155",
  },
  langBtnActive: {
    borderColor: "#ff6b35",
    backgroundColor: "rgba(255,107,53,0.15)",
  },
  langFlag: {
    fontSize: 16,
  },
  langText: {
    fontSize: 12,
    color: "#94a3b8",
    fontWeight: "600",
  },
  langTextActive: {
    color: "#ff6b35",
    fontWeight: "700",
  },
  infoLine: {
    fontSize: 12,
    color: "#cbd5e1",
    marginVertical: 2,
  },
});
