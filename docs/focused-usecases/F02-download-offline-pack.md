# F02 — Tải Gói Sử Dụng Offline

## 1. Thông Tin Nhận Diện

- **Use Case ID:** F02 (Tải gói sử dụng offline), F03 (Cập nhật gói), F04 (Sửa lỗi gói), F05 (Xóa gói)
- **Use Case Name:** Quản lý gói dữ liệu ngoại tuyến (Offline Pack)
- **Module / System Boundary:** Phân hệ Ngoại tuyến Mobile (Offline Service) & Backend API
- **Primary Actor:** Khách du lịch (Tourist)
- **Supporting Actors:** Không có
- **Maturity:** Focused
- **Implementation Status:** Đã code & Đã kiểm thử (`mobile/src/screens/OfflineScreen.js`, `OfflinePackService.js`)
- **Scope:** [H/G]; user-goal
- **Summary / Goal:** Du khách chủ động tải trước gói dữ liệu tham quan Quận 4 (bao gồm danh sách POI, tọa độ Geofence, kịch bản thuyết minh và các tuyến tour) về bộ nhớ máy điện thoại. Nhờ đó, ứng dụng hoạt động mượt mà khi đi vào các ngõ hẻm mất sóng 4G hoặc khi bật chế độ máy bay.
- **Version / Change Reference:** v1.0 / Focused-Spec

---

## 2. Điều Kiện & Quy Tắc

- **Trigger:** Du khách bấm nút "Offline" trên bản đồ và chọn "Tải Gói Dữ Liệu Quận 4 Về Máy".
- **Preconditions:** Thiết bị có kết nối mạng tại thời điểm tải và đủ dung lượng bộ nhớ trống.
- **Assumptions:** Bộ nhớ thiết bị còn tối thiểu 50 MB trống.
- **Success Postconditions:** Dữ liệu POI và tour được lưu nguyên tử vào `tourvoice_offline_manifest` trong AsyncStorage; trạng thái gói chuyển thành "ĐÃ SẴN SÀNG NGOẠI TUYẾN".
- **Minimum Guarantees:** Quá trình tải bị ngắt giữa chừng (mất mạng, kill app) không làm hỏng hoặc xóa mất gói offline cũ đang hoạt động (`BR-OFFLINE-01`); xóa gói không làm mất các cài đặt ứng dụng khác (`BR-OFFLINE-02`).
- **Business Rules Liên Quan:** `BR-OFFLINE-01`, `BR-OFFLINE-02`.

---

## 3. Basic Course of Events (Luồng Sự Kiện Cơ Bản)

| Step ID | Actor Action | System Response | BR / Nhánh liên quan |
|---|---|---|---|
| **F02.B1** | Bấm nút "Offline" trên bản đồ | Mở màn hình `OfflineScreen`, kiểm tra xem máy đã có gói tải trước nào chưa | — |
| **F02.B2** | Bấm "Tải Gói Dữ Liệu Quận 4" | Bắt đầu quy trình tải 4 bước: Hiển thị thanh trạng thái tiến trình | E1 |
| **F02.B3** | — | Bước 1/4: Tải danh sách toàn bộ POI kèm bản dịch qua `GET /api/v1/pois?limit=100` | E2 |
| **F02.B4** | — | Bước 2/4: Tải thông tin các tuyến tour đi bộ qua `GET /api/v1/tours` | — |
| **F02.B5** | — | Bước 3/4: Kiểm tra tính toàn vẹn (Staging): Xác minh số lượng điểm, dung lượng byte | BR-OFFLINE-01 |
| **F02.B6** | — | Bước 4/4: Lưu trữ nguyên tử (Atomic Commit) vào bộ nhớ thiết bị | — |
| **F02.B7** | Xem thông báo hoàn tất | Hiển thị huy hiệu xanh "ĐÃ SẴN SÀNG NGOẠI TUYẾN", số điểm dừng, dung lượng chiếm dụng và danh sách điểm đã lưu | A1, A2 |

---

## 4. Alternative Paths (Các Nhánh Thay Thế)

- **F02.A1 — Cập nhật / Đồng bộ lại gói (F03/F04)**:
  - **Điểm rẽ:** Tại bước `F02.B7` khi gói đã tồn tại, khách bấm "Cập Nhật / Đồng Bộ Lại".
  - **Hành vi:** `OfflinePackService` tải phiên bản mới nhất từ server, kiểm tra tính toàn vẹn rồi ghi đè an toàn lên bản ghi cũ.
- **F02.A2 — Xóa gói ngoại tuyến (F05)**:
  - **Điểm rẽ:** Tại bước `F02.B7`, khách bấm "Xóa Gói".
  - **Hành vi:** Hệ thống hiển thị hộp thoại xác nhận; khi xác nhận, giải phóng bộ nhớ, xóa `tourvoice_offline_manifest` và đưa giao diện về trạng thái ban đầu (`BR-OFFLINE-02`).

---

## 5. Exception Paths (Các Nhánh Ngoại Lệ)

- **F02.E1 — Không đủ bộ nhớ trống**:
  - **Điểm phát sinh:** Tại bước `F02.B2` khi thiết bị hết dung lượng lưu trữ.
  - **Phản hồi:** Thông báo "Bộ nhớ thiết bị không đủ để lưu trữ gói ngoại tuyến".
- **F02.E2 — Mất kết nối mạng khi đang tải**:
  - **Điểm phát sinh:** Tại bước `F02.B3` hoặc `F02.B4` khi mạng bị ngắt.
  - **Phản hồi:** Dừng tiến trình, hiển thị "Lỗi tải gói: Mất kết nối mạng", giữ nguyên vẹn gói cũ trước đó nếu có (`BR-OFFLINE-01`).

---

## 6. Extension Points

- Không có extension point riêng.

---

## 7. Truy Vết Triển Khai & Nghiệm Thu

- **Sơ đồ liên quan:** SD06 (Tải gói offline), AD06 (Activity offline pack).
- **Màn hình UI:** `mobile/src/screens/OfflineScreen.js`.
- **Services:** `mobile/src/services/OfflinePackService.js`, `mobile/src/services/api.js`.
- **Bằng chứng kiểm thử:** Thao tác tải, cập nhật và xóa gói trên `OfflineScreen.js`.
