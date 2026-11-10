# Phạm vi Web App

Cập nhật ngày 10/11/2026 theo yêu cầu chỉ giữ Web App.

- Một frontend React tại `apps/web-admin`, gồm cổng du khách `/client/`, chủ sạp `/owner/` và quản trị `/admin/`.
- Máy tính và điện thoại truy cập bằng trình duyệt; có PWA, không phát hành APK/IPA hay ứng dụng Expo.
- FastAPI, worker dịch/TTS, MongoDB và các API nghiệp vụ tiếp tục phục vụ Web App.
- GPS dùng quyền vị trí trình duyệt. HTTPS cần thiết khi truy cập từ thiết bị khác; không cam kết định vị/phát nền liên tục khi trình duyệt hoặc hệ điều hành tạm ngừng trang.
- Logic geofence ở `shared/geofence.js`, kiểm thử bằng `node --test shared/tests/*.test.mjs`.
- CI kiểm thử backend, MongoDB, web, GPS, luồng trình duyệt và container. Không còn bước build native.

Các báo cáo Word, hình sơ đồ và tài liệu thiết kế có nhắc React Native/Expo được lập trước thay đổi này là tài liệu lịch sử; chúng không mô tả phạm vi phát hành hiện tại. Khi xuất lại báo cáo/sơ đồ cần dùng Web App và các giới hạn trình duyệt nêu trên.
