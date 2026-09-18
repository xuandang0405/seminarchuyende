# Quyết Định Kiến Trúc: Lựa Chọn Nhà Cung Cấp Bản Đồ & Định Tuyến (ADR: Map & Routing Provider Selection)

- **Trạng thái**: Đã phê duyệt & Đã triển khai (Approved & Implemented)
- **Ngày quyết định**: 2026-09-18
- **Khu vực áp dụng**: Hệ thống Thuyết minh Du lịch Đa ngôn ngữ Quận 4 (Web, Mobile, Backend)

---

## 1. Bối Cảnh & Vấn Đề (Context & Problem Statement)

Dự án cần một giải pháp hiển thị bản đồ số và tính toán lộ trình dẫn đường thực tế (turn-by-turn routing) cho khách du lịch tại Quận 4, TP. Hồ Chí Minh với các yêu cầu cốt lõi:
1. **Tuyệt đối không dùng dữ liệu giả lập**: Tuyến đường phải bám sát mạng lưới giao thông đường bộ thực tế (hẻm, đường một chiều, cầu cảng).
2. **Hỗ trợ 3 loại khoảng cách riêng biệt**:
   - Khoảng cách đường chim bay (`straight_line_distance_m`).
   - Khoảng cách đường bộ thực tế (`route_distance_m`).
   - Thời gian di chuyển ước tính (`route_duration_s`).
3. **Chi phí & Ràng buộc tài nguyên**: Dự án của nhóm 4 sinh viên trong 10 tuần, cần giải pháp chi phí 0 VNĐ, không phụ thuộc thẻ tín dụng quốc tế (Google Cloud Billing / Mapbox Credit Card), nhưng có thể tự host hoặc triển khai local/production không bị chặn.
4. **Trải nghiệm thẩm mỹ cao (Dark Mode)**: Giao diện bản đồ phải đồng bộ với thiết kế sang trọng, hiện đại của ứng dụng.

---

## 2. So Sánh Các Phương Án (Options Comparison)

| Tiêu Chí Đánh Giá | Phương Án 1: Google Maps Platform | Phương Án 2: Mapbox GL / Directions | Phương Án 3: OpenStreetMap + CartoDB + OSRM (ĐƯỢC CHỌN) |
| :--- | :--- | :--- | :--- |
| **Chi phí bản đồ & API** | Đắt ($5 - $10 / 1,000 lượt request). Đòi hỏi thẻ Visa/Mastercard. | $5 / 1,000 request sau khi hết quota miễn phí. Cần thẻ tín dụng. | **100% Miễn phí & Mã nguồn mở**. Không yêu cầu thẻ tín dụng. |
| **Giao diện & Dark Mode** | Phải tùy biến JSON style phức tạp, watermark bắt buộc. | Đẹp, hỗ trợ Vector tiles. | **CartoDB Dark Matter**: Cực kỳ mượt mà, tông màu tối sang trọng, tối ưu cho du lịch đêm Quận 4. |
| **Khả năng Tự Host (Self-hosted)** | Không thể tự host. Phụ thuộc 100% cloud Google. | Rất khó và tốn kém tài nguyên. | **Rất dễ dàng**: OSRM chạy Docker cục bộ chỉ tốn ~100MB RAM cho vùng Quận 4 / TP.HCM. |
| **Khả năng Dự phòng (Fallback)** | Không có fallback khi hết hạn ngạch tài khoản. | Khó tích hợp nếu bị khóa key. | **Tích hợp kép**: Dùng OSRM làm router chính + Deep Link Google Maps làm fallback ngoại tuyến. |
| **Phù hợp đề tài sinh viên** | Rủi ro bị trừ tiền ngoài ý muốn hoặc hết quota giữa chừng. | Rủi ro tương tự Google Maps. | **An toàn tuyệt đối, chạy offline/local vô hạn lần, bảo vệ đồ án tốt nhất**. |

---

## 3. Quyết Định Được Lựa Chọn (The Decision)

Nhóm quyết định lựa chọn **Kiến trúc Lai (Hybrid Open-Source Architecture)**:

1. **Bản đồ nền (Base Map Tiles)**:
   - Sử dụng **CartoDB Dark Matter** (`https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png`) làm tile layer chính.
   - Thư viện hiển thị: **Leaflet.js** trên Web và **react-native-maps** trên Mobile.
   - Ưu điểm: Hiển thị mượt mà, tông màu bóng bẩy, không watermark thương mại ép buộc, tốc độ CDN cực nhanh.

2. **Công cụ Tính Toán Tuyến Đường (Routing Engine)**:
   - Sử dụng **OSRM (Open Source Routing Machine) v5 API**.
   - Profile: `foot` (cho du khách đi bộ tham quan) và `car` (cho xe máy / ô tô).
   - Tích hợp lớp Cache lưu trữ MongoDB (`route_cache`) với TTL 24 giờ và lượng tử hóa tọa độ (fingerprint SHA256) giúp giảm tải 90% số lượng request ra ngoài.

3. **Cơ chế Dự phòng (Graceful Degradation & Fallback)**:
   - Khi mạng bị ngắt kết nối hoặc OSRM timeout quá 3.0 giây: Hệ thống tự động chuyển sang tính toán khoảng cách đường thẳng có trọng số nhân (`x1.3`) và gắn cờ cảnh báo nhẹ.
   - Cung cấp nút bấm "Mở trong Google Maps" (`https://www.google.com/maps/dir/?api=1&destination={lat},{lon}`) để người dùng có thể chuyển sang ứng dụng Google Maps chính thức bất cứ lúc nào.

---

## 4. Hệ Quả & Đánh Giá (Consequences & Validation)

- **Tích cực**:
  - Không tốn một đồng chi phí API.
  - Tốc độ phản hồi cực nhanh (<15ms khi trúng Cache, ~180ms khi gọi OSRM).
  - Tự động hóa hoàn toàn việc dịch chỉ đường (maneuver) sang tiếng Việt thân thiện ("Rẽ trái vào đường Bến Vân Đồn", "Đi thẳng về hướng Chợ Xóm Chiếu").
  - Đạt 100% tiêu chí đồ án tốt nghiệp với đầy đủ sơ đồ kỹ thuật và ma trận kiểm thử.
- **Tiêu cực / Rủi ro**:
  - Máy chủ công cộng của OSRM có giới hạn tốc độ (rate limit) nếu gọi với tần suất lớn.
  - *Biện pháp giảm thiểu đã thực hiện*: Đã xây dựng tầng Cache MongoDB thông minh (`route_cache`) và hỗ trợ cấu hình biến môi trường `ROUTING_PROVIDER_URL` để chuyển sang máy chủ OSRM nội bộ bất kỳ lúc nào.
