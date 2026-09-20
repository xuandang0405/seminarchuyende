import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { Camera, CameraView } from "expo-camera";
import { api } from "../services/api";

export default function QRScanScreen({ onBack, onPlayAudio, onStartTour }) {
  const [hasPermission, setHasPermission] = useState(null);
  const [scanned, setScanned] = useState(false);

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === "granted");
    })();
  }, []);

  const handleBarcodeScanned = async ({ type, data }) => {
    if (scanned) return;
    setScanned(true);

    try {
      let tourId = null;
      let poiId = null;
      let qrCode = (data || "").trim();

      // Check if scanned data is a Tour or POI URL / Scheme
      if (qrCode.includes("type=tour") || qrCode.includes("tourguide://tour/")) {
        const match = qrCode.match(/id=([^&]+)/) || qrCode.match(/tour=([^&]+)/) || qrCode.match(/tourguide:\/\/tour\/([^\/\?]+)/);
        if (match) tourId = match[1];
      } else if (qrCode.includes("type=poi") || qrCode.includes("tourguide://poi/")) {
        const match = qrCode.match(/id=([^&]+)/) || qrCode.match(/poi=([^&]+)/) || qrCode.match(/tourguide:\/\/poi\/([^\/\?]+)/);
        if (match) poiId = match[1];
      } else if (qrCode.includes("tourguide://qr/")) {
        qrCode = qrCode.replace("tourguide://qr/", "").trim();
      } else if (qrCode.includes("qr=")) {
        const match = qrCode.match(/qr=([^&]+)/);
        if (match) qrCode = match[1];
      }

      // If directly a Tour URL / ID
      if (tourId) {
        const tourDetail = await api.getTourDetail(tourId, "vi");
        if (tourDetail) {
          Alert.alert(
            "Tuyến Tour Quận 4",
            `Đã nhận diện tuyến tour: ${tourDetail.name || tourDetail.title}\n(${tourDetail.pois?.length || 0} điểm dừng)`,
            [
              {
                text: "Bắt Đầu Tour",
                onPress: () => {
                  if (onStartTour) onStartTour(tourDetail);
                  onBack();
                },
              },
              { text: "Đóng", onPress: () => setScanned(false), style: "cancel" },
            ]
          );
          return;
        }
      }

      // If directly a POI URL / ID
      if (poiId) {
        const poiDetail = await api.getPOIDetail(poiId, "vi");
        if (poiDetail) {
          Alert.alert(
            "Điểm Tham Quan",
            `Đã nhận diện: ${poiDetail.name || poiDetail.code}`,
            [
              {
                text: "Nghe Thuyết Minh",
                onPress: () => {
                  if (onPlayAudio) onPlayAudio(poiDetail, "qr");
                  onBack();
                },
              },
              { text: "Đóng", onPress: () => setScanned(false), style: "cancel" },
            ]
          );
          return;
        }
      }

      // Otherwise resolve via QR service API
      const result = await api.resolveQR(qrCode, "vi");
      if (result && (result.target_type === "tour" || result.tour)) {
        const tour = result.tour;
        Alert.alert(
          "Tuyến Tour Quận 4",
          `Đã nhận diện tuyến tour: ${tour?.name || result.tour_id || "Khám phá Quận 4"}\n(${tour?.pois?.length || 0} điểm dừng)`,
          [
            {
              text: "Bắt Đầu Tour",
              onPress: () => {
                if (onStartTour) onStartTour(tour || { _id: result.tour_id });
                onBack();
              },
            },
            { text: "Đóng", onPress: () => setScanned(false), style: "cancel" },
          ]
        );
      } else if (result && result.poi) {
        Alert.alert(
          "Điểm Tham Quan",
          `Đã nhận diện: ${result.poi.name || result.poi.code}`,
          [
            {
              text: "Nghe Thuyết Minh",
              onPress: () => {
                if (onPlayAudio) onPlayAudio(result.poi, "qr");
                onBack();
              },
            },
            { text: "Đóng", onPress: () => setScanned(false), style: "cancel" },
          ]
        );
      } else {
        Alert.alert("Lỗi", "Không tìm thấy thông tin cho mã QR này", [
          { text: "Quét lại", onPress: () => setScanned(false) },
        ]);
      }
    } catch (err) {
      Alert.alert("Lỗi", "Không thể kết nối đến máy chủ", [
        { text: "Quét lại", onPress: () => setScanned(false) },
      ]);
    }
  };

  if (hasPermission === null) {
    return (
      <View style={styles.center}>
        <Text style={styles.text}>Đang xin quyền truy cập Camera...</Text>
      </View>
    );
  }

  if (hasPermission === false) {
    return (
      <View style={styles.center}>
        <Text style={styles.text}>Không có quyền truy cập Camera để quét QR.</Text>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Text style={styles.backBtnText}>← Quay Lại Bản Đồ</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView
        style={StyleSheet.absoluteFillObject}
        onBarcodeScanned={scanned ? undefined : handleBarcodeScanned}
        barcodeScannerSettings={{
          barcodeTypes: ["qr"],
        }}
      />

      <View style={styles.overlay}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Text style={styles.backBtnText}>← Quay Lại</Text>
        </TouchableOpacity>

        <View style={styles.scanFrame}>
          <Text style={styles.scanPrompt}>Hướng camera vào mã QR dán tại điểm đến</Text>
        </View>

        {scanned && (
          <TouchableOpacity style={styles.rescanBtn} onPress={() => setScanned(false)}>
            <Text style={styles.rescanText}>Chạm để quét lại</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#0f172a",
    padding: 20,
  },
  text: {
    color: "#fff",
    fontSize: 16,
    textAlign: "center",
    marginBottom: 20,
  },
  overlay: {
    flex: 1,
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 50,
  },
  backBtn: {
    alignSelf: "flex-start",
    marginLeft: 20,
    backgroundColor: "rgba(15, 23, 42, 0.8)",
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  backBtnText: {
    color: "#fff",
    fontWeight: "700",
  },
  scanFrame: {
    width: 260,
    height: 260,
    borderWidth: 2,
    borderColor: "#ff6b35",
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(255, 107, 53, 0.05)",
  },
  scanPrompt: {
    position: "absolute",
    bottom: -40,
    color: "#fff",
    fontSize: 13,
    textAlign: "center",
    backgroundColor: "rgba(0,0,0,0.6)",
    paddingVertical: 4,
    paddingHorizontal: 12,
    borderRadius: 6,
  },
  rescanBtn: {
    backgroundColor: "#ff6b35",
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  rescanText: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 15,
  },
});
