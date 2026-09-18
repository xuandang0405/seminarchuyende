# Đặc Tả Ca Sử Dụng Chuyên Sâu: Bản Đồ & Tuyến Đường Thực Tế (Focused Use Cases: T01 - T05 - T14 - T17)

Tài liệu này đặc tả chi tiết 4 ca sử dụng trọng tâm liên quan đến Bản đồ số, Tìm kiếm POI, Định tuyến thực tế OSRM và Thuyết minh tự động theo vị trí GPS tại Quận 4.

---

## 1. T01: Khám Phá Bản Đồ Thực Tế & Lọc Theo Khung Nhìn (Map Discovery & Viewport Filtering)

### 1.1. Thông Tin Chung
- **Mã UC**: T01
- **Tác nhân chính**: Du khách (Web / Mobile)
- **Tiền điều kiện**: Thiết bị có kết nối mạng và mở màn hình Bản đồ.
- **Hậu điều kiện**: Bản đồ hiển thị chính xác các POI nằm trong ranh giới Quận 4 với tọa độ thực tế.

### 1.2. Luồng Sự Kiện Chính (Main Flow)
1. Ứng dụng gửi yêu cầu `GET /api/v1/map/config`.
2. Hệ thống trả về tâm Quận 4 (`lat: 10.7635, lon: 106.7042`), độ phóng to mặc định `15`, ranh giới bounding box và tile URL CartoDB Dark Matter.
3. Ứng dụng khởi tạo bản đồ số và tải danh sách POI trong khung nhìn hiện tại qua `GET /api/v1/pois/in-bounds?min_lat=...&min_lon=...&max_lat=...&max_lon=...`.
4. Backend sử dụng truy vấn MongoDB không gian `$geoWithin` với `$box` để lấy danh sách POI.
5. Ứng dụng vẽ các Marker tương ứng lên bản đồ kèm hiệu ứng động.

### 1.3. Luồng Ngoại Lệ (Exception Flow)
- **E01**: Người dùng cuộn bản đồ ra ngoài phạm vi Quận 4.
  - Hệ thống tự động giới hạn (maxBounds) hoặc trả về danh sách rỗng, khuyến khích người dùng quay trở lại khu vực Quận 4.

---

## 2. T05: Tìm Kiếm & Lọc POI Đa Ngôn Ngữ (POI Search & Category Filtering)

### 2.1. Thông Tin Chung
- **Mã UC**: T05
- **Tác nhân chính**: Du khách
- **Tiền điều kiện**: Đang ở màn hình Bản đồ.
- **Hậu điều kiện**: Danh sách POI và các Marker trên bản đồ được lọc theo từ khóa và danh mục được chọn.

### 2.2. Luồng Sự Kiện Chính (Main Flow)
1. Người dùng nhập từ khóa tìm kiếm vào thanh Search (ví dụ: "chợ") hoặc bấm vào chip danh mục (ví dụ: "Ẩm thực").
2. Ứng dụng thực hiện cơ chế Debounce 300ms nhằm giảm thiểu request thừa.
3. Gửi yêu cầu `GET /api/v1/pois/search?q=chợ&category=culinary&lang=vi`.
4. Backend tìm kiếm đa tiêu chí trên tên, mô tả, địa chỉ và các bản dịch đa ngôn ngữ (`localizations`).
5. Kết quả trả về được chuẩn hóa sang DTO kèm thông tin cự ly đường chim bay nếu có vị trí GPS người dùng.
6. Bản đồ cập nhật lại Marker và danh sách thẻ bên dưới.

---

## 3. T14: Xem Trước & Dẫn Đường Từng Bước Thực Tế (Turn-by-turn Navigation OSRM)

### 3.1. Thông Tin Chung
- **Mã UC**: T14
- **Tác nhân chính**: Du khách, Routing Engine OSRM
- **Tiền điều kiện**: Đã xác định được tọa độ xuất phát (GPS hoặc nhấp chọn trên bản đồ) và POI đích đến.
- **Hậu điều kiện**: Tuyến đường thực tế được hiển thị bằng Polyline chi tiết kèm danh sách hướng dẫn từng bước.

### 3.2. Luồng Sự Kiện Chính (Main Flow)
1. Người dùng bấm nút "Chỉ đường" trên thẻ POI hoặc bấm vào một điểm trên bản đồ để chọn điểm xuất phát.
2. Ứng dụng gửi yêu cầu `POST /api/v1/routes/preview` với payload:
   ```json
   {
     "origin": { "latitude": 10.76814, "longitude": 106.70678 },
     "destination_poi_id": "poi_ben_nha_rong",
     "mode": "walking",
     "locale": "vi"
   }
   ```
3. Backend lượng tử hóa tọa độ, tính toán SHA256 fingerprint và kiểm tra trong MongoDB collection `route_cache`.
4. Nếu có cache hợp lệ (TTL 24h), trả về ngay lập tức. Nếu chưa có, gọi OSRM v5 API.
5. OSRM trả về cự ly đường bộ (`route_distance_m`), thời gian di chuyển (`route_duration_s`), hình học LineString và các bước rẽ.
6. Backend dịch các câu lệnh maneuver sang tiếng Việt và lưu vào `route_cache`.
7. Client vẽ Polyline màu xanh biển lên bản đồ và hiển thị bảng chỉ dẫn từng bước (Directions Panel trên Web / Navigation HUD trên Mobile).

### 3.3. Luồng Ngoại Lệ & Reroute (Alternative & Exception Flows)
- **A01: Micro-distance (< 8m)**:
  - Nếu khoảng cách giữa xuất phát và đích < 8 mét, hệ thống ngắt ngắn mạch (short-circuit), trả về ngay kết quả 0m, 0s với hướng dẫn "Bạn đã ở ngay điểm đến", không cần gọi ra ngoài.
- **A02: Tái định tuyến Mobile khi lệch đường**:
  - Khi đang di chuyển, nếu người dùng lệch khỏi Polyline > 35m trong 2 mẫu GPS liên tiếp và đã qua thời gian cooldown 15s, ứng dụng tự động gửi lại request để tính tuyến đường mới từ vị trí hiện tại.
- **E01: OSRM gián đoạn mạng**:
  - Backend kích hoạt Fallback tính đường thẳng x 1.3 và trả về cờ `fallback: true`. Client thông báo nhẹ và cung cấp nút "Mở Google Maps" dự phòng.

---

## 4. T17: Phát Hiện Đến Nơi & Thuyết Minh Tự Động (Arrival & Auto-narration Handshake)

### 4.1. Thông Tin Chung
- **Mã UC**: T17
- **Tác nhân chính**: Du khách, GPS Thiết bị, Audio Player
- **Tiền điều kiện**: Ứng dụng đang trong trạng thái dẫn đường (`NAVIGATING`).
- **Hậu điều kiện**: Nhận diện người dùng đã tới đích, dừng dẫn đường và tự động phát bài thuyết minh điểm đến.

### 4.2. Luồng Sự Kiện Chính (Main Flow)
1. Trong quá trình di chuyển, `LocationService` liên tục cập nhật tọa độ GPS mới.
2. `NavigationController` tính khoảng cách thẳng đến đích (`calculateDistanceMeters`).
3. Khi cự ly <= 15 mét (Arrival Threshold), hệ thống chuyển trạng thái sang `ARRIVED`.
4. Màn hình hiển thị Banner chúc mừng "🎉 Bạn đã đến nơi!".
5. Đồng thời, `GeofenceEngine` xác nhận người dùng nằm trong bán kính kích hoạt (`trigger_radius`) của POI, kiểm tra debounce (>= 3s) và cooldown (5 phút).
6. `GeofenceEngine` phát tín hiệu sang `NarrationController` để tự động tải và phát bài thuyết minh âm thanh bằng ngôn ngữ người dùng đã chọn.
7. Thanh phát âm thanh `AudioPlayerBar` mở lên và bắt đầu phát bài thuyết minh.
