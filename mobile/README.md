# TourVoice Mobile App (React Native + Google Maps)

Ứng dụng di động du khách cho hệ thống Thuyết minh Du lịch Đa ngôn ngữ Quận 4.

## 1. Tính Năng Nổi Bật
- **Bản đồ toàn màn hình (Google Maps)**: Sử dụng `react-native-maps` (`provider={PROVIDER_GOOGLE}`), hiển thị rõ nét toàn bộ khu vực Quận 4.
- **Định vị thời gian thực**: Hiển thị chấm tròn xanh vị trí GPS của người dùng (`showsUserLocation={true}`).
- **Vòng tròn Geofence**: Hiển thị trực quan bán kính vào (vòng xanh) và bán kính rời khỏi (vòng nét đứt).
- **Thuyết minh tự động**: Khi du khách di chuyển bước vào vùng Geofence của địa điểm nào, app tự động phát bài thuyết minh âm thanh kèm cơ chế chống lặp (cooldown).
- **Thanh phát âm thanh nổi (Bottom Player Bar)**: Play/Pause, tua tiến trình, đóng player.
- **Quét mã QR bằng Camera**: Quét mã dán tại quán ăn/di tích để nghe thuyết minh ngay lập tức khi GPS yếu trong nhà.
- **Lưu trữ ngoại tuyến (Offline Mode)**: Tải trước toàn bộ tour để sử dụng khi mất mạng 4G.

---

## 2. Hướng Dẫn Cài Đặt & Chạy Thử

### Yêu Cầu Trước:
- Node.js (v18+) & npm hoặc yarn.
- Cài đặt ứng dụng **Expo Go** trên điện thoại thật (tải từ Google Play Store hoặc Apple App Store) hoặc dùng Máy ảo Android Studio / Xcode Simulator.

### Bước 1: Cài đặt thư viện
Mở terminal tại thư mục `seminarchuyende/mobile/`:
```bash
npm install
```

### Bước 2: Cấu hình địa chỉ IP máy chủ (Backend)
Mở file `src/services/api.js`:
- Nếu chạy trên **máy ảo Android (Android Emulator)**: Giữ nguyên `http://10.0.2.2:8000/api/v1`.
- Nếu chạy trên **máy ảo iOS (iOS Simulator)**: Giữ nguyên `http://localhost:8000/api/v1`.
- Nếu chạy trên **điện thoại thật qua Expo Go**: Đổi thành địa chỉ IP máy tính của bạn trong mạng Wifi (ví dụ: `http://192.168.1.50:8000/api/v1`).

### Bước 3: Khởi chạy
```bash
npx expo start
```
- Mở ứng dụng **Expo Go** trên điện thoại, quét mã QR hiển thị trên màn hình terminal để trải nghiệm ứng dụng ngay trên điện thoại của bạn!
- Hoặc bấm phím `a` để mở trên Android Emulator, phím `i` để mở trên iOS Simulator.
