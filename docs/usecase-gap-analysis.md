# Use Case Gap Analysis — Hệ thống Thuyết minh Du lịch Đa ngôn ngữ

Tài liệu đối chiếu và phân tích khoảng cách (Gap Analysis) giữa mô hình Use Case ban đầu, mẫu đặc tả Focused Use Cases (`FocusedUseCases.doc`), và hiện trạng triển khai thực tế trong codebase.

---

## 1. Bảng Tổng Hợp Phân Loại Khoảng Cách (Gap Matrix)

| GAP_ID | Nguồn & UC liên quan | Hiện trạng có bằng chứng | Điểm thiếu / Mâu thuẫn | Loại | Tác động Code / Schema / Sơ đồ / Test | Cách xử lý | Trạng thái |
|---|---|---|---|---|---|---|---|
| **GAP-01** | Toàn bộ 65 UCs | Đã có catalog sơ lược trong `usecase_catalog.md` và `requirements-traceability.md` | Thiếu định dạng chuẩn Focused UC (Actor Action / System Response, Alt/Exc paths, Min Guarantees, Pre/Post conditions) | **DOC** | Tài liệu đặc tả | Lập template chuẩn và viết bộ hồ sơ Focused UC cho từng nhóm chức năng | **ĐÃ XỬ LÝ** |
| **GAP-02** | Toàn bộ quy tắc nghiệp vụ (BR) | Các quy tắc như 3s debounce, 5m cooldown, readiness gate đã được code trong service | Chưa có bảng Business Rules tập trung với mã định danh ổn định (`BR-AUTH-01` đến `BR-TOUR-01`) | **DOC** | Tài liệu quy tắc | Xây dựng `docs/business-rules.md` liên kết trực tiếp tới mã nguồn và test | **ĐÃ XỬ LÝ** |
| **GAP-03** | U01 & các UC có bảo vệ (C01, C02, O04, O05...) | Sơ đồ use case trước đây có nơi mô hình hóa `include U01` gây hiểu nhầm mỗi thao tác đều phải đăng nhập lại | Phiên đăng nhập hợp lệ là Precondition, không phải là bước con được gọi lại trong phiên | **MODEL** | Sơ đồ Use Case (PlantUML & Eraser) | Rà soát và loại bỏ association include U01 thừa; giữ U01 là Precondition ở tầng service | **ĐÃ XỬ LÝ** |
| **GAP-04** | O05 (Gửi nội dung) & C07 (Duyệt nội dung) | Hai nghiệp vụ xảy ra ở hai thời điểm khác nhau bởi hai actor khác nhau (Owner và Admin) | Tránh mô hình hóa O05 include C07 hoặc ngược lại | **MODEL** | Sơ đồ Use Case & SD10 | Giữ O05 và C07 là 2 Use Case độc lập; liên kết qua trạng thái `pending` của document `poi_submissions` | **ĐÃ XỬ LÝ** |
| **GAP-05** | T08, T09, T11 & N01, N02 | Mobile đã triển khai `NarrationController` đơn cho cả 3 nguồn kích hoạt (Bấm tay, GPS, QR) | Sơ đồ cần thể hiện rõ T08/T09/T11 include N01; N02 chỉ là conditional extension khi thiếu audio | **MODEL** | Sơ đồ Use Case & AD16 | Giữ `T08/T09/T11 ..> N01 : <<include>>` và `N02 ..> N01 : <<extend>>` | **ĐÃ XỬ LÝ** |
| **GAP-06** | F08 (Consent) & T13 (Tour) | Code mobile `TourSessionService` đã tách biệt phiên đi tour local với `AnalyticsOutbox` | Sơ đồ và đặc tả cần khẳng định: Từ chối consent vẫn được đi tour và dùng toàn bộ tính năng | **BEHAVIOR** | Mobile code & test | Giữ nguyên `AnalyticsOutbox` kiểm tra consent trước khi ghi event; tour chạy độc lập | **ĐÃ XỬ LÝ** |
| **GAP-07** | C07 (Review) & C04 (Publish / Readiness Gate) | Backend `poi_admin_service.py` đã chặn publish nếu thiếu tiếng Anh/audio | Admin duyệt nội dung chủ quán không tự động kích hoạt public ngay nếu chưa qua Readiness Gate | **BEHAVIOR** | Backend service & test | Giữ logic tách biệt `poi_submissions.status = approved` và `POI.is_active` | **ĐÃ XỬ LÝ** |
| **GAP-08** | S10 (Xuất báo cáo), S12 (Cấu hình), S13 (Backup) | Danh mục chứa nhãn `[P]` (Proposal) | Chưa chốt luồng nghiệp vụ chi tiết của S10, S12, S13 | **SCOPE_PROPOSAL** | Backlog quản trị | Giữ nguyên trạng thái P trong backlog, không tự ý coi là đã hoàn thành | **GIỮ BACKLOG** |

---

## 2. Kết Luận Định Hướng

1. **Không thay đổi Database Schema**: 28 MongoDB collections và 9 SQLite tables hiện tại đáp ứng trọn vẹn toàn bộ yêu cầu của đồ án.
2. **Không đổi Stack**: Giữ nguyên FastAPI + PyMongo Async + React Vite + React Native Expo.
3. **Trực tiếp sửa sơ đồ**: Cập nhật cả PlantUML và Eraser cho các ranh giới actor, quan hệ include/extend theo đúng chuẩn UML.
