# Mobile Background Behavior & Geofencing Specification

Tài liệu này phân biệt rõ ràng các cấp độ hoạt động nền (background behavior) trên hệ điều hành Android và iOS, nhằm đảm bảo kỳ vọng thực tế khi nghiệm thu và demo đề tài.

---

## 1. Phân biệt 3 Cấp độ Hoạt động Nền (Background Levels)

| Mức độ | Hành vi cụ thể | Khả năng hỗ trợ trên Android | Khả năng hỗ trợ trên iOS | Giải pháp kiến trúc / Fallback |
|---|---|---|---|---|
| **Mức 1** | **Lấy vị trí khi app ở background** | Hoạt động tốt qua Foreground Service (`expo-location` + Sticky Notification). | Hoạt động qua Background Location Update (yêu cầu quyền "Always Allow"). | Sử dụng `Location.startLocationUpdatesAsync` kèm thông báo hệ thống trên Android để giữ service. |
| **Mức 2** | **Tiếp tục audio đang phát khi khóa màn hình** | Hoạt động ổn định với Audio Focus và cấu hình `staysActiveInBackground: true`. | Hoạt động ổn định khi cấu hình `UIBackgroundModes: ["audio"]`. | Cấu hình Audio session ở mức native, hiển thị media notification trên màn hình khóa. |
| **Mức 3** | **Tự động bắt đầu phát audio mới từ GPS khi app ở background / màn hình khóa** | Bị hạn chế bởi chính sách Background Audio Start của Android 12+ (hạn chế bắt đầu media playback từ background). | Bị hạn chế nghiêm ngặt bởi chính sách iOS (không cho phép tự phát âm thanh khi app chưa active). | **Hành vi Fallback chuẩn hóa**: Khi phát hiện vào vùng POI lúc app đang nền, hệ thống gửi một **Heads-up Notification** (vd: *"Bạn đang ở gần Bến Nhà Rồng - Chạm để nghe thuyết minh"*). Người dùng chạm vào thông báo để mở app và audio tự động phát ngay lập tức. |

---

## 2. Thông số Cấu hình Geofencing & Chống Rung (Hysteresis)

Toàn bộ các thông số được tập trung cấu hình tại `apps/mobile/src/config/geofenceConfig.ts`:

- **Bán kính kích hoạt mặc định (`DEFAULT_TRIGGER_RADIUS`)**: `30.0` mét.
- **Bán kính thoát vùng (`EXIT_HYSTERESIS_RADIUS`)**: `45.0` mét (lớn hơn bán kính vào vùng 15m để tránh hiện tượng GPS dao động ở rìa mép tạo sự kiện vào/ra liên tục).
- **Thời gian debounce (`DEBOUNCE_INTERVAL_MS`)**: `3000` ms (vị trí phải ổn định trong vùng tối thiểu 3 giây mới kích hoạt).
- **Thời gian hồi (`COOLDOWN_PERIOD_MS`)**: `300000` ms (5 phút). Sau khi phát thành công thuyết minh một địa điểm, POI đó sẽ bị khóa không tự động phát lại trong vòng 5 phút trừ khi người dùng chủ động bấm nghe.
- **Độ chính xác GPS tối thiểu (`MAX_ACCEPTABLE_ACCURACY_M`)**: `35.0` mét. Các mẫu GPS có sai số lớn hơn 35m sẽ bị loại bỏ để tránh kích hoạt sai địa điểm.
- **Thời gian tối đa của mẫu GPS (`MAX_SAMPLE_AGE_MS`)**: `10000` ms (10 giây). Bỏ qua các vị trí cũ được lưu tạm (cached GPS).
