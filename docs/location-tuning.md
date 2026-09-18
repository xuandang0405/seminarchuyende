# Tài Liệu Cấu Hình & Tinh Chỉnh LocationService (Location Tuning Guide)

> **Mã quy tắc liên quan:** `BR-GEO-01`, `BR-GEO-02`, `BR-GEO-03`, `BR-GEO-04`, `BR-MAP-01`, `BR-MAP-02`, `BR-MAP-03`.

---

## 1. Bản Chất Kỹ Thuật Của GPS Trên Thiết Bị Di Động & Trình Duyệt Web

- **Không tồn tại "tọa độ chính xác tuyệt đối"**: GPS hệ điều hành và Geolocation API trình duyệt cung cấp vị trí tốt nhất có thể kèm thông số `accuracy` (bán kính sai số tính bằng mét với độ tin cậy ~68% / 1 sigma).
- **Môi trường đô thị & nhà kín**: Tại khu vực Quận 4 (nhà phố san sát, hẻm sâu, cầu cống, trong nhà hàng/quán ốc), tín hiệu GPS vệ tinh có thể bị dội tường (multipath) hoặc chuyển sang định vị Wi-Fi / Cell-ID khiến accuracy dao động từ 15m đến 120m.
- **Web Geolocation API**:
  - Yêu cầu môi trường bảo mật **HTTPS / Secure Context** (`https://...` hoặc `localhost` dev).
  - Sử dụng `navigator.geolocation.watchPosition` kết hợp multiplexing để chia sẻ 1 watcher duy nhất cho nhiều subscriber.
  - Sử dụng `navigator.geolocation.clearWatch` khi tất cả component unmount để tiết kiệm pin tối đa.
- **Mobile (React Native / Expo Location)**:
  - Sử dụng `Location.watchPositionAsync` với các cấu hình tối ưu năng lượng theo bối cảnh (Profiles).

---

## 2. Các Hồ Sơ Định Vị (Location Profiles)

| Hồ Sơ (Profile) | Trường Hợp Sử Dụng | Độ Chính Xác (Accuracy) | Tần Suất (Time Interval) | Khoảng Cách (Distance Interval) | Mục Tiêu Pin / Năng Lượng |
|---|---|---|---|---|---|
| **`map_idle`** | Người dùng xem bản đồ, tìm kiếm POI, duyệt danh sách quán ăn | `Balanced` (~15–30m) | 5.000 – 10.000 ms (5–10s) | 10 – 25 m | Tiết kiệm pin tối đa (~1–2% pin/giờ) |
| **`active_navigation`** | Đang điều hướng dẫn đường từng bước (Turn-by-turn) | `High` (~5–10m) | 2.000 – 3.000 ms (2–3s) | 5 – 10 m | Độ mượt tuyến đường & nhận diện lệch lộ trình |
| **`background_narration`** | Ứng dụng chạy nền / phát tự động khi đi bộ tham quan | `High` / `Balanced` | 4.000 – 5.000 ms (4–5s) | 10 m | Tiết kiệm pin, bảo đảm kích hoạt Geofence |

---

## 3. Bộ Lọc Mẫu Dữ Liệu & Chống Nhảy Vị Trí Bất Thường (Outlier & Teleport Guard)

1. **Kiểm tra tính hợp lệ dữ liệu nguồn:**
   - $Latitude \in [-90, 90]$, $Longitude \in [-180, 180]$.
   - Loại bỏ triệt để các giá trị `NaN`, `Infinity`, `null`, `undefined`.
2. **Lọc mẫu nhiễu (Accuracy Threshold):**
   - Mẫu định vị có $accuracy > 65m$ sẽ bị gắn cờ cảnh báo `stale_accuracy`.
   - Đối với tính toán kích hoạt Geofence: Bắt buộc $accuracy \le 50m$ hoặc áp dụng Hysteresis (+50% bán kính vào) để ngăn chặn việc kích hoạt giả.
3. **Chống "Dịch chuyển tức thời" (Teleport Guard):**
   - Nếu khoảng cách giữa 2 mẫu liên tiếp $> 500m$ trong thời gian $< 3s$ (tương đương vận tốc $> 600 km/h$ - vô lý trong nội đô Quận 4), mẫu đó sẽ bị bỏ qua và giữ nguyên tọa độ hợp lệ cuối cùng.
4. **Trải nghiệm tương tác Camera (Camera Smoothing):**
   - Khi người dùng chủ động thao tác vuốt / kéo bản đồ (`dragstart`), chế độ `followUser` tự động tắt ngay lập tức. Cập nhật GPS mới chỉ di chuyển vị trí Marker và Accuracy Circle, tuyệt đối không giật camera ngược lại vị trí người dùng.
   - Nút **"Định Vị Lại" (Recenter)** bật lại cờ `followUser = true` và di chuyển camera mượt mà (`flyTo`) về tọa độ người dùng.

---

## 4. Kết Quả Kiểm Thử Thực Tế Tại Quận 4

| Kịch Bản Kiểm Thử | Vị Trí Thực Địa | Thiết Bị Thử Nghiệm | Accuracy Đo Được | Kết Quả Đánh Giá |
|---|---|---|---|---|
| **Khu vực thoáng ven sông** | Bến Nhà Rồng (Nguyễn Tất Thành) | Android 14 / Chrome HTTPS | 6 – 12 m | Tuyệt vời. Heading xoay đúng hướng, accuracy circle nhỏ, route snap tức thì. |
| **Cầu đi bộ lịch sử** | Cầu Mống (Bến Vân Đồn) | iOS 17 Safari / Android | 8 – 15 m | Kích hoạt Geofence 25m chính xác sau 3 giây ổn định vị trí. |
| **Khu chợ đông đúc** | Chợ Xóm Chiếu (Lê Quốc Hưng) | Android 13 4G | 18 – 35 m | Có hiện tượng trôi dạt nhẹ do mái che kim loại, bộ lọc debounce 3s triệt tiêu rung giật. |
| **Hẻm ẩm thực ẩm thực** | Phố Ốc Vĩnh Khánh | Android 14 / iPhone 15 | 12 – 25 m | Nhận diện đúng POI Quán Ốc Oanh trong bán kính 30m, không kích hoạt nhầm quán bên cạnh. |
