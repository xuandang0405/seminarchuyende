import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { Camera, CameraView } from "expo-camera";
import { api } from "../services/api";

export default function QRScanScreen({ onBack, onPlayAudio }) {
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

    // Extract QR code ID from tourguide://qr/<id> or direct ID
    let qrId = data;
    if (data.includes("tourguide://qr/")) {
      qrId = data.replace("tourguide://qr/", "").trim();
    }

    try {
      const result = await api.resolveQR(qrId, "vi");
      if (result && result.poi) {
        Alert.alert(
          "Quét Thành Công!",
          `Đã nhận diện: ${result.poi.code}`,
          [
            {
              text: "Nghe Thuyết Minh",
              onPress: () => {
                if (onPlayAudio) onPlayAudio(result.poi, "qr");
                onBack();
              },
            },
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
