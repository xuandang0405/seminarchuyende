# Analytics Contract & Metrics Specification

Tài liệu này quy định cấu trúc sự kiện, hợp đồng dữ liệu, cơ chế đồng thuận (consent), hàng chờ outbox và công thức tính toán chỉ số thống kê.

---

## 1. Nguyên tắc Riêng tư & Đồng thuận (Privacy & Consent)

1. **Độc lập hoàn toàn**: Quyền truy cập vị trí thiết bị (Location Permission) phục vụ định vị GPS không đồng nghĩa với việc đồng ý thu thập phân tích. Khách du lịch từ chối Analytics vẫn sử dụng đầy đủ 100% tính năng bản đồ, nghe thuyết minh, quét QR và tải offline.
2. **Mã định danh giả danh (Pseudonymous)**: `device_id` là UUID ngẫu nhiên tạo cục bộ trên client khi người dùng đồng ý. Không liên kết với tài khoản người dùng hoặc số điện thoại.
3. **Thu hồi Consent**: Khi người dùng tắt consent trong Settings, ứng dụng ngay lập tức ngừng sinh sự kiện mới và xóa toàn bộ sự kiện đang chờ trong `analytics_outbox` cục bộ.

---

## 2. Hợp đồng Sự kiện Analytics (`analytics_events`)

Mọi sự kiện gửi lên server qua endpoint `POST /api/v1/analytics/events/batch` phải tuân theo cấu trúc sau:

```json
{
  "events": [
    {
      "event_id": "550e8400-e29b-41d4-a716-446655440000",
      "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "poi_id": "poi_ben_nha_rong",
      "event_type": "audio_start",
      "occurred_at": "2026-09-16T10:15:30.000Z",
      "properties": {
        "playback_id": "pb_123456789",
        "lang": "vi",
        "trigger_source": "gps",
        "position_ms": 0
      }
    }
  ]
}
```

### Các Loại Event (`event_type`):
- `poi_view`: Xem chi tiết địa điểm.
- `audio_start`: Bắt đầu phát audio (`playback_id` bắt đầu).
- `audio_progress`: Tiến độ nghe tích lũy (`listened_ms`, `current_position_ms`).
- `audio_end`: Kết thúc hoặc dừng audio (`completed`: boolean, `total_listened_ms`).
- `qr_scan`: Quét mã QR thành công.
- `tour_start`: Bắt đầu một tour.
- `tour_end`: Kết thúc tour.
- `search`: Tìm kiếm POI (`query`, `results_count`).

---

## 3. Cơ chế Khử Trùng Lặp & Batch ACK (Idempotent Ingestion)

1. **Ổn định Event ID**: `event_id` được sinh tại Mobile Client và giữ nguyên khi retry mạng.
2. **Batch Ingestion**: Client gửi tối đa 50 sự kiện/lần.
3. **Phản hồi Từng Sự kiện (Per-event ACK)**:
   ```json
   {
     "success_count": 48,
     "duplicate_count": 2,
     "failed_count": 0,
     "acked_ids": ["550e8400-e29b-41d4-a716-446655440000", "..."]
   }
   ```
4. Client chỉ xóa khỏi SQLite `analytics_outbox` những sự kiện nằm trong danh sách `acked_ids`.

---

## 4. Công thức Tính Toán Chỉ số Thống kê

- **Timezone Thống kê**: Mặc định `Asia/Ho_Chi_Minh` (UTC+7).
- **`audio_plays`**: Số lượng `playback_id` bắt đầu thành công, khử trùng theo `playback_id`.
- **`listened_ms`**: Thời gian thực tế ở trạng thái playing (không tính thời gian pause hoặc buffering). Lấy giá trị tích lũy lớn nhất của mỗi `playback_id`.
- **`listens_count`**: Số lượt nghe có `listened_ms > 0`.
- **Thời gian nghe trung bình (Average Listening Time)**:
  $$\text{Avg Duration} = \begin{cases} \frac{\sum \text{listened\_ms}}{\text{listens\_count}} & \text{khi } \text{listens\_count} > 0 \\ 0 & \text{khi } \text{listens\_count} = 0 \end{cases}$$
  Tuyệt đối tránh lỗi chia cho 0 khi chưa có lượt nghe nào.
