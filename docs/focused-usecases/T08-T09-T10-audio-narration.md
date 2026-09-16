# T08, T09 & T10 — Thuyết Minh Âm Thanh & Điều Khiển

## 1. Thông Tin Nhận Diện

- **Use Case ID:** T08 (Bấm nghe theo yêu cầu), T09 (Nghe tự động khi đến gần POI theo GPS), T10 (Điều khiển phát thuyết minh)
- **Use Case Name:** Phát và điều khiển thuyết minh âm thanh
- **Module / System Boundary:** Phân hệ Ứng dụng Di động Khách du lịch (Mobile)
- **Primary Actor:** Khách du lịch (Tourist)
- **Supporting Actors:** Dịch vụ GPS định vị thiết bị (`LocationService`), Trình phát âm thanh native (`expo-av`)
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`mobile/tests/geofence.test.js` 6/6 tests passed)
- **Scope:** [H/G]; user-goal
- **Summary / Goal:** Khách du lịch nghe bài thuyết minh âm thanh giới thiệu về địa điểm tham quan Quận 4 thông qua 2 phương thức: chủ động bấm nút "Nghe Thuyết Minh" trên modal chi tiết hoặc tự động kích hoạt khi di chuyển vào bán kính Geofence của địa điểm. Khách có thể tạm dừng, tiếp tục hoặc dừng bài nghe qua thanh điều khiển `AudioPlayerBar`.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:**
  - T08: Khách bấm nút "Nghe Thuyết Minh Âm Thanh" trên `POIDetailModal`.
  - T09: `GeofenceEngine` phát hiện tọa độ GPS của khách nằm trong `trigger_radius` liên tục trong 3 giây (Debounce).
  - T10: Khách bấm nút Play/Pause hoặc Close (X) trên `AudioPlayerBar`.
- **Preconditions:** Ứng dụng đang mở. Đối với T09, quyền vị trí GPS đã được cấp.
- **Assumptions:** Thiết bị có loa ngoài hoặc tai nghe hoạt động bình thường.
- **Success Postconditions:** Audio stream được nạp và phát; giao diện hiển thị thanh phát âm thanh đồng bộ; cooldown 5 phút được áp dụng cho POI sau khi phát thành công (`BR-GEO-02`).
- **Minimum Guarantees:** Một thời điểm chỉ có 1 audio được phát (tránh phát đè); GPS không ngắt bài khách đang chủ động nghe; nút Stop ngăn tự phát lại trong cùng vùng (`BR-AUDIO-01`).
- **Business Rules Liên Quan:** `BR-GEO-01`, `BR-GEO-02`, `BR-AUDIO-01`, `BR-AUDIO-02`, `BR-AUDIO-03`, `BR-CONSENT-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **T08.B1** | Bấm nút "Nghe Thuyết Minh" (hoặc GPS kích hoạt T09) | `NarrationController` nhận yêu cầu phát với `poi`, `triggerType` và `currentLang` | BR-AUDIO-01, E1 |
| **T08.B2** | — | Kiểm tra ưu tiên: Nếu đang phát do người dùng bấm tay mà GPS kích hoạt thì bỏ qua GPS | BR-AUDIO-01 |
| **T08.B3** | — | Gọi `AudioSourceResolver` phân giải nguồn: Bộ nhớ máy (Offline) → Remote URL → Fallback ngôn ngữ | BR-AUDIO-03, A1 |
| **T08.B4** | — | Nạp file audio qua `expo-av`, bắt đầu phát và hiển thị thanh `AudioPlayerBar` | BR-AUDIO-02, E2 |
| **T08.B5** | Lắng nghe bài thuyết minh | Thanh player hiển thị tiêu đề, phụ đề, nút Play/Pause và nhãn nguồn (TỰ ĐỘNG / BẤM TAY) | — |
| **T08.B6** | Bấm nút Play/Pause (T10) | Tạm dừng hoặc tiếp tục phát, ghi nhận thời gian nghe thực tế `listened_ms` | BR-METRIC-01 |
| **T08.B7** | Bài nghe phát hết (hoặc bấm Stop) | `NarrationController` ghi nhận hoàn thành, đánh dấu cooldown 5 phút cho POI trong `GeofenceEngine` | BR-GEO-02, BR-EVENT-01 |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **T08.A1 — Nghe ngoại tuyến khi mất mạng (Offline Playback)**:
  - **Điểm rẽ:** Tại bước `T08.B3` khi thiết bị đang ở chế độ máy bay hoặc mất sóng.
  - **Hành vi:** `AudioSourceResolver` nạp file âm thanh từ gói offline đã lưu trữ (`tourvoice_offline_manifest`). Bài nghe phát bình thường từ bộ nhớ điện thoại.
- **T08.A2 — Người dùng bấm nút Stop (X) khi đang ở trong vùng**:
  - **Điểm rẽ:** Tại bước `T08.B6`, người dùng chủ động bấm nút tắt player.
  - **Hành vi:** `GeofenceEngine` đánh dấu triệt tiêu (suppress) POI này, ngăn hệ thống tự động phát lại bài này cho đến khi khách thực sự di chuyển ra ngoài bán kính thoát (Hysteresis exit radius).

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **T08.E1 — Mẫu GPS kém chính xác (> 35m)**:
  - **Điểm phát sinh:** Tại bước kiểm tra Geofence (T09).
  - **Phản hồi:** Mẫu GPS bị loại bỏ theo `BR-GEO-01`, không phát sinh sự kiện sai lệch.
- **T08.E2 — Lỗi tải file âm thanh**:
  - **Điểm phát sinh:** Tại bước `T08.B4` khi file audio không tồn tại hoặc lỗi mạng.
  - **Phản hồi:** Trạng thái chuyển sang `ERROR`, hiển thị phụ đề văn bản thay thế, không làm đóng ứng dụng.

---

## 6. Extension Points

- Không có extension point riêng (`N01` được gọi theo quan hệ `<<include>>`).

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD04 (GPS nhận diện địa điểm), AD04 (Activity GPS), AD16 (Narration dùng chung).
- **Màn hình UI:** `mobile/src/screens/MapScreen.js`, `mobile/src/components/AudioPlayerBar.js`, `mobile/src/components/POIDetailModal.js`.
- **Services & Modules:**
  - `mobile/src/services/LocationService.js`
  - `mobile/src/services/GeofenceEngine.js`
  - `mobile/src/services/NarrationController.js`
  - `mobile/src/services/AudioSourceResolver.js`
- **Bằng chứng kiểm thử:** `mobile/tests/geofence.test.js` (6/6 tests passed).
