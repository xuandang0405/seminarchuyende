import React, { useState } from "react";
import { StatusBar } from "expo-status-bar";
import { StyleSheet, View } from "react-native";
import MapScreen from "./src/screens/MapScreen";
import QRScanScreen from "./src/screens/QRScanScreen";
import OfflineScreen from "./src/screens/OfflineScreen";

import { narrationController } from "./src/services/NarrationController";

export default function App() {
  const [currentScreen, setCurrentScreen] = useState("map"); // "map" | "qr" | "offline"

  return (
    <View style={styles.container}>
      <StatusBar style="light" />

      {currentScreen === "map" && (
        <MapScreen
          onNavigateQR={() => setCurrentScreen("qr")}
          onNavigateOffline={() => setCurrentScreen("offline")}
        />
      )}

      {currentScreen === "qr" && (
        <QRScanScreen
          onBack={() => setCurrentScreen("map")}
          onPlayAudio={(poi) => {
            narrationController.requestNarration(poi, "qr");
            setCurrentScreen("map");
          }}
        />
      )}

      {currentScreen === "offline" && (
        <OfflineScreen onBack={() => setCurrentScreen("map")} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
});
