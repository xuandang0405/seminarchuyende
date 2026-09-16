# N01 & N02 — Subflows Điều Phối Phát & Chuẩn Bị Thuyết Minh

## 1. Thông Tin Nhận Diện

- **Use Case ID:** N01 (Phát nội dung thuyết minh), N02 (Chuẩn bị thuyết minh theo yêu cầu)
- **Use Case Name:** Subflow điều phối phát và chuẩn bị thuyết minh
- **Module / System Boundary:** Phân hệ Audio Controller Mobile & Pipeline TTS Backend
- **Primary Actor:** Hệ thống (Internal Subflow, được gọi bởi T08, T09, T11)
- **Supporting Actors:** Dịch vụ Edge-TTS, Storage Adapter
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử
- **Scope:** [H]; supporting-subflow
- **Summary / Goal:** `N01` là subflow dùng chung quản lý state machine của trình phát âm thanh, xử lý xung đột, ưu tiên phát và hủy bài cũ. `N02` là subflow mở rộng (`<<extend>>`), chỉ kích hoạt khi ngôn ngữ yêu cầu chưa có sẵn file âm thanh trên thiết bị/server để tạo audio on-demand qua TTS.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Được gọi khi có yêu cầu phát từ T08, T09 hoặc T11.
- **Preconditions:** Tham số `poi` hợp lệ.
- **Assumptions:** File âm thanh có thể tải từ URL hoặc đọc từ file cục bộ.
- **Success Postconditions:** Audio stream được phát tới tai du khách; cập nhật thời gian nghe `listened_ms`.
- **Minimum Guarantees:** Không phát chồng 2 nguồn âm thanh cùng lúc; không phát kết quả của request cũ nếu du khách đã đổi ngôn ngữ (`BR-AUDIO-01`, `BR-AUDIO-02`).
- **Business Rules Liên Quan:** `BR-AUDIO-01`, `BR-AUDIO-02`, `BR-AUDIO-03`, `BR-JOB-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **N01.B1** | (Kích hoạt từ T08/T09/T11) | Nhận POI, ngôn ngữ và token yêu cầu | — |
| **N01.B2** | — | Xác định ưu tiên: Dừng bài cũ nếu bài mới có độ ưu tiên cao hơn (Manual > GPS) | BR-AUDIO-01 |
| **N01.B3** | — | Phân giải nguồn audio qua `AudioSourceResolver` | BR-AUDIO-03, A1 |
| **N01.B4** | — | Khởi tạo sound object native (`expo-av`), lắng nghe sự kiện playback status | E1 |
| **N01.B5** | — | Bắt đầu phát âm thanh, thông báo trạng thái `PLAYING` tới giao diện | — |
| **N01.B6** | — | Khi bài kết thúc, kích hoạt callback thành công, cập nhật cooldown | BR-GEO-02 |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **N01.A1 — N02 Chuẩn bị audio on-demand qua TTS**:
  - **Điểm rẽ:** Tại bước `N01.B3` khi chưa có file âm thanh cho ngôn ngữ mong muốn và có mạng.
  - **Hành vi:** `N02` gửi yêu cầu tạo audio tới backend (`POST /api/v1/audio/tts`), chờ trong giới hạn timeout (5s); nếu hoàn tất kịp, phát file mới; nếu không kịp, fallback về tiếng Anh hoặc tiếng Việt (`BR-AUDIO-03`).

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **N01.E1 — Lỗi phát âm thanh native**:
  - **Điểm phát sinh:** Tại bước `N01.B4` khi file hỏng hoặc codec không hỗ trợ.
  - **Phản hồi:** Chuyển trạng thái `ERROR`, không đánh dấu cooldown để cho phép du khách thử lại sau.

---

## 6. Extension Points

- `N02` mở rộng tại bước `N01.B3` với điều kiện `[thiếu audio phù hợp và có kết nối mạng]`.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** AD16 (Narration dùng chung), SD07 (Worker tạo audio).
- **Mã nguồn:** `mobile/src/services/NarrationController.js`, `backend/app/services/tts_service.py`.
- **Bằng chứng kiểm thử:** `mobile/tests/geofence.test.js`, `backend/tests/test_poi_full_slice.py`.
