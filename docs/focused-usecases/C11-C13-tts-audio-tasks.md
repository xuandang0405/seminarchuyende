# C11 & C13 — Tạo Audio Bằng TTS & Điều Khiển Tác Vụ Nền

## 1. Thông Tin Nhận Diện

- **Use Case ID:** C11 (Tạo audio bằng TTS), C12 (Theo dõi tiến độ), C13 (Tạm dừng/tiếp tục/hủy tác vụ)
- **Use Case Name:** Tạo audio bằng TTS và điều khiển tác vụ nền
- **Module / System Boundary:** Phân hệ Xử lý Âm thanh Backend & Web Admin
- **Primary Actor:** Quản trị viên (Admin có quyền `content:publish` hoặc `poi:update`)
- **Supporting Actors:** Dịch vụ Edge-TTS (`edge-tts 7.2.8`), File Storage Adapter
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`tts_service.py`, `backend/storage/audio/`)
- **Scope:** [H]; user-goal
- **Summary / Goal:** Quản trị viên kích hoạt quá trình chuyển đổi văn bản mô tả điểm tham quan thành giọng đọc nhân tạo đa ngôn ngữ (tiếng Việt, tiếng Anh, tiếng Pháp) thông qua Edge-TTS. Hệ thống tạo file MP3 thật, lưu trữ vào volume storage và liên kết URL với bản dịch POI.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Admin bấm nút "Tạo Thuyết Minh Bằng AI (TTS)" trên giao diện quản trị POI.
- **Preconditions:** POI đã có văn bản mô tả hoặc bản dịch tương ứng.
- **Assumptions:** Kết nối Internet sẵn sàng để gọi Edge-TTS.
- **Success Postconditions:** Tạo thành công file `.mp3` trong `backend/storage/audio/`; cập nhật trường `audio_url` trong `poi_localizations`; tạo bản ghi task với `status='completed'`.
- **Minimum Guarantees:** Worker claim task có lease có thời hạn; không ghi đè audio cũ nếu version nội dung đã thay đổi trong lúc TTS đang chạy (`BR-JOB-01`).
- **Business Rules Liên Quan:** `BR-JOB-01`, `BR-AUDIO-03`, `BR-POI-01`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **C11.B1** | Bấm nút "Tạo Thuyết Minh (TTS)" trên POI | Hiển thị hộp thoại chọn ngôn ngữ (`vi`, `en`, `fr`) và giọng đọc | — |
| **C11.B2** | Chọn cấu hình và bấm "Bắt Đầu Tạo" | Gửi `POST /api/v1/audio/tts` với `{ poi_id, lang, voice }` | BR-JOB-01 |
| **C11.B3** | — | Backend tạo task trong `audio_tasks` với `status='running'`, kích hoạt service Edge-TTS | E1 |
| **C11.B4** | — | Edge-TTS tổng hợp âm thanh giọng đọc nhân tạo, lưu file MP3 vào thư mục storage | — |
| **C11.B5** | — | Cập nhật `poi_localizations.audio_url`, hoàn tất task (`status='succeeded'`) | BR-POI-01 |
| **C11.B6** | Nghe thử file audio đã tạo | Admin bấm nút Play nghe thử trực tiếp trên Web Admin; hiển thị thời lượng audio | — |

---

## 4. Alternative Paths

- Không có nhánh thay thế.

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **C11.E1 — Lỗi kết nối dịch vụ TTS**:
  - **Điểm phát sinh:** Tại bước `C11.B3` khi Edge-TTS bị timeout hoặc mạng gián đoạn.
  - **Phản hồi:** Task chuyển trạng thái `failed`, lưu `error_message`, hiển thị nút "Thử lại" cho Admin.

---

## 6. Extension Points

- `C13 Điều khiển tác vụ` mở rộng tại `C12` cho phép Admin yêu cầu hủy (`cancel_requested=True`) nếu task chạy quá lâu.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD07 (Worker tạo audio), AD07 (Activity TTS).
- **Màn hình UI:** `apps/web-admin/src/pages/POIList.tsx`.
- **API Endpoints:**
  - `POST /api/v1/audio/tts`
  - `GET /api/v1/audio/tasks/{task_id}`
- **Service & Storage:** `app/services/tts_service.py`, `backend/storage/audio/`, Collection: `audio_tasks`, `poi_localizations`.
- **Bằng chứng kiểm thử:** File âm thanh MP3 thực tế được sinh tại `backend/storage/audio/` và bài test `test_poi_full_slice.py`.
