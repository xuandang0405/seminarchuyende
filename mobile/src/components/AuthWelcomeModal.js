import React, { useState } from "react";
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "../services/api";

export default function AuthWelcomeModal({ visible, onClose, onSuccess }) {
  const [mode, setMode] = useState("welcome"); // "welcome" | "login" | "register"
  const [loading, setLoading] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleContinueAsGuest = async () => {
    setLoading(true);
    try {
      const guestRes = await api.createGuestSession();
      if (!guestRes || !guestRes.guest_token) {
        throw new Error("Không thể khởi tạo phiên khách");
      }
      await AsyncStorage.setItem("tourvoice_guest_token", guestRes.guest_token);
      onSuccess({ type: "guest", guestToken: guestRes.guest_token, user: null });
      onClose();
    } catch (err) {
      Alert.alert("Lỗi", err.message || "Không thể kết nối máy chủ");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Thông báo", "Vui lòng nhập đầy đủ Email và Mật khẩu.");
      return;
    }
    setLoading(true);
    try {
      const res = await api.login(email.trim(), password.trim());
      const token = res.access_token || res.token;
      const user = res.user;

      await AsyncStorage.setItem("tourvoice_user_token", token);
      await AsyncStorage.setItem("tourvoice_user", JSON.stringify(user));

      // Check if there was an existing guest session to claim
      const existingGuestToken = await AsyncStorage.getItem("tourvoice_guest_token");
      if (existingGuestToken) {
        await api.claimGuestSession(existingGuestToken, token);
        await AsyncStorage.removeItem("tourvoice_guest_token");
      }

      onSuccess({ type: "user", userToken: token, user });
      onClose();
    } catch (err) {
      Alert.alert("Đăng nhập thất bại", err.message || "Email hoặc mật khẩu không đúng.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!fullName.trim() || !email.trim() || !password.trim()) {
      Alert.alert("Thông báo", "Vui lòng điền đầy đủ các thông tin bắt buộc.");
      return;
    }
    if (password.length < 6) {
      Alert.alert("Thông báo", "Mật khẩu phải có độ dài tối thiểu 6 ký tự.");
      return;
    }
    if (password !== confirmPassword) {
      Alert.alert("Thông báo", "Mật khẩu xác nhận không khớp.");
      return;
    }

    setLoading(true);
    try {
      const existingGuestToken = await AsyncStorage.getItem("tourvoice_guest_token");
      const res = await api.registerTourist(fullName.trim(), email.trim(), password.trim(), existingGuestToken);

      const token = res.access_token || res.token;
      const user = res.user;

      await AsyncStorage.setItem("tourvoice_user_token", token);
      await AsyncStorage.setItem("tourvoice_user", JSON.stringify(user));
      if (existingGuestToken) {
        await AsyncStorage.removeItem("tourvoice_guest_token");
      }

      Alert.alert("Thành công", "Đăng ký tài khoản du khách thành công!");
      onSuccess({ type: "user", userToken: token, user });
      onClose();
    } catch (err) {
      Alert.alert("Đăng ký thất bại", err.message || "Email đã tồn tại hoặc không hợp lệ.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={true}>
      <View style={styles.overlay}>
        <View style={styles.container}>
          <Text style={styles.brandEmoji}>🎙️</Text>
          <Text style={styles.title}>TourVoice Quận 4</Text>
          <Text style={styles.subtitle}>Hệ Thống Thuyết Minh Du Lịch Đa Ngôn Ngữ</Text>

          {mode === "welcome" && (
            <View style={styles.buttonGroup}>
              <TouchableOpacity
                style={[styles.btn, styles.btnGuest]}
                onPress={handleContinueAsGuest}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#0f172a" />
                ) : (
                  <Text style={styles.btnGuestText}>🚶 Tiếp tục với tư cách Khách</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.btn, styles.btnLogin]}
                onPress={() => setMode("login")}
              >
                <Text style={styles.btnText}>🔑 Đăng Nhập Tài Khoản</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.btn, styles.btnRegister]}
                onPress={() => setMode("register")}
              >
                <Text style={styles.btnRegisterText}>📝 Đăng Ký Du Khách Mới</Text>
              </TouchableOpacity>
            </View>
          )}

          {mode === "login" && (
            <View style={styles.form}>
              <Text style={styles.formTitle}>Đăng Nhập Du Khách</Text>
              <TextInput
                style={styles.input}
                placeholder="Email của bạn"
                placeholderTextColor="#64748b"
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
              />
              <TextInput
                style={styles.input}
                placeholder="Mật khẩu"
                placeholderTextColor="#64748b"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />
              <TouchableOpacity
                style={[styles.btn, styles.btnPrimary]}
                onPress={handleLogin}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.btnText}>Xác Nhận Đăng Nhập</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity style={styles.linkBtn} onPress={() => setMode("register")}>
                <Text style={styles.linkText}>Chưa có tài khoản? Đăng ký ngay</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.linkBtn} onPress={() => setMode("welcome")}>
                <Text style={styles.linkTextSecondary}>← Quay lại màn hình chính</Text>
              </TouchableOpacity>
            </View>
          )}

          {mode === "register" && (
            <View style={styles.form}>
              <Text style={styles.formTitle}>Đăng Ký Tài Khoản</Text>
              <TextInput
                style={styles.input}
                placeholder="Họ và tên du khách"
                placeholderTextColor="#64748b"
                value={fullName}
                onChangeText={setFullName}
              />
              <TextInput
                style={styles.input}
                placeholder="Email"
                placeholderTextColor="#64748b"
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
              />
              <TextInput
                style={styles.input}
                placeholder="Mật khẩu (tối thiểu 6 ký tự)"
                placeholderTextColor="#64748b"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />
              <TextInput
                style={styles.input}
                placeholder="Xác nhận mật khẩu"
                placeholderTextColor="#64748b"
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry
              />
              <TouchableOpacity
                style={[styles.btn, styles.btnPrimary]}
                onPress={handleRegister}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.btnText}>Hoàn Tất Đăng Ký</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity style={styles.linkBtn} onPress={() => setMode("login")}>
                <Text style={styles.linkText}>Đã có tài khoản? Đăng nhập</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.linkBtn} onPress={() => setMode("welcome")}>
                <Text style={styles.linkTextSecondary}>← Quay lại màn hình chính</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(15, 23, 42, 0.85)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  container: {
    backgroundColor: "#1e293b",
    width: "100%",
    maxWidth: 400,
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: "#334155",
    alignItems: "center",
  },
  brandEmoji: {
    fontSize: 48,
    marginBottom: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: "bold",
    color: "#ff6b35",
    textAlign: "center",
  },
  subtitle: {
    fontSize: 13,
    color: "#94a3b8",
    textAlign: "center",
    marginTop: 4,
    marginBottom: 20,
  },
  buttonGroup: {
    width: "100%",
    gap: 12,
  },
  btn: {
    width: "100%",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  btnGuest: {
    backgroundColor: "#00b4d8",
  },
  btnGuestText: {
    color: "#0f172a",
    fontSize: 15,
    fontWeight: "bold",
  },
  btnLogin: {
    backgroundColor: "#ff6b35",
  },
  btnRegister: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "#475569",
  },
  btnRegisterText: {
    color: "#cbd5e1",
    fontSize: 14,
    fontWeight: "600",
  },
  btnPrimary: {
    backgroundColor: "#10b981",
    marginTop: 6,
  },
  btnText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "bold",
  },
  form: {
    width: "100%",
  },
  formTitle: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#e2e8f0",
    marginBottom: 12,
    textAlign: "center",
  },
  input: {
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "#334155",
    color: "#ffffff",
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
    marginBottom: 10,
    fontSize: 14,
  },
  linkBtn: {
    marginTop: 10,
    alignItems: "center",
  },
  linkText: {
    color: "#00b4d8",
    fontSize: 13,
  },
  linkTextSecondary: {
    color: "#94a3b8",
    fontSize: 12,
  },
});
