import React, { useState, useEffect } from "react";
import { StatusBar } from "expo-status-bar";
import { StyleSheet, View, Alert } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import AsyncStorage from "@react-native-async-storage/async-storage";
import MapScreen from "./src/screens/MapScreen";
import QRScanScreen from "./src/screens/QRScanScreen";
import OfflineScreen from "./src/screens/OfflineScreen";
import AuthWelcomeModal from "./src/components/AuthWelcomeModal";

import { narrationController } from "./src/services/NarrationController";
import { tourSessionService } from "./src/services/TourSessionService";

export default function App() {
  const [currentScreen, setCurrentScreen] = useState("map"); // "map" | "qr" | "offline"
  const [session, setSession] = useState(null);
  const [showAuthModal, setShowAuthModal] = useState(false);

  useEffect(() => {
    restoreSession();

    // Subscribe to narration state to intercept trial consent & paywall
    const unsubscribe = narrationController.subscribe((snapshot) => {
      if (snapshot.lastErrorCode === "TRIAL_CONSENT_REQUIRED" && snapshot.poi) {
        Alert.alert(
          "🎁 Lượt Nghe Thử Miễn Phí",
          `Bạn đang có 1 lượt nghe thử miễn phí duy nhất cho địa điểm "${snapshot.poi.name}". Bạn có muốn kích hoạt lượt nghe thử này ngay bây giờ?`,
          [
            { text: "Để sau", style: "cancel" },
            {
              text: "Đồng ý nghe thử",
              onPress: () => {
                narrationController.requestNarration(
                  snapshot.poi,
                  snapshot.triggerType || "manual",
                  snapshot.currentLang || "vi",
                  true // user_consent_trial = true
                );
              },
            },
          ]
        );
      } else if (
        snapshot.lastErrorCode === "TOUR_PURCHASE_REQUIRED" ||
        snapshot.lastErrorCode === "TRIAL_EXHAUSTED"
      ) {
        Alert.alert(
          "🔒 Cần Mua Tour",
          "Bạn đã dùng hết lượt nghe thử miễn phí. Vui lòng đăng nhập và mua tour để mở khóa toàn bộ bài thuyết minh.",
          [
            { text: "Đóng", style: "cancel" },
            {
              text: "Đăng Nhập / Đăng Ký",
              onPress: () => setShowAuthModal(true),
            },
          ]
        );
      }
    });

    return () => unsubscribe();
  }, []);

  const restoreSession = async () => {
    try {
      const userToken = await AsyncStorage.getItem("tourvoice_user_token");
      const userStr = await AsyncStorage.getItem("tourvoice_user");
      const guestToken = await AsyncStorage.getItem("tourvoice_guest_token");

      if (userToken && userStr) {
        const user = JSON.parse(userStr);
        setSession({ type: "user", userToken, user });
        narrationController.setSession(userToken, null);
      } else if (guestToken) {
        setSession({ type: "guest", guestToken, user: null });
        narrationController.setSession(null, guestToken);
      } else {
        // Chưa có phiên: Bật màn hình chào Đăng nhập / Đăng ký / Tiếp tục khách
        setShowAuthModal(true);
      }
    } catch (e) {
      console.warn("Lỗi khôi phục session:", e);
      setShowAuthModal(true);
    }
  };

  const handleAuthSuccess = (newSession) => {
    setSession(newSession);
    narrationController.setSession(newSession.userToken, newSession.guestToken);
  };

  return (
    <SafeAreaProvider>
      <View style={styles.container}>
        <StatusBar style="light" />

        {currentScreen === "map" && (
          <MapScreen
            session={session}
            onNavigateQR={() => setCurrentScreen("qr")}
            onNavigateOffline={() => setCurrentScreen("offline")}
            onOpenAuth={() => setShowAuthModal(true)}
          />
        )}

        {currentScreen === "qr" && (
          <QRScanScreen
            onBack={() => setCurrentScreen("map")}
            onPlayAudio={(poi) => {
              narrationController.requestNarration(poi, "qr");
              setCurrentScreen("map");
            }}
            onStartTour={async (tour) => {
              await tourSessionService.startTour(tour);
              setCurrentScreen("map");
            }}
          />
        )}

        {currentScreen === "offline" && (
          <OfflineScreen onBack={() => setCurrentScreen("map")} session={session} />
        )}

        <AuthWelcomeModal
          visible={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          onSuccess={handleAuthSuccess}
        />
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
});

