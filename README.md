# TourVoice Quận 4

Hệ thống thuyết minh du lịch tự động đa ngôn ngữ: React Web App cho du khách, chủ sạp và quản trị viên, FastAPI và PyMongo Async cho API, MongoDB replica set để lưu dữ liệu và xử lý giao dịch.

API dùng ba lớp router → service → repository. Tiến trình worker riêng xử lý tác vụ dịch và tạo audio qua hàng đợi bền vững trong MongoDB. Không cần Redis cho luồng hiện tại.

## Chạy bằng Docker

Cần Docker Compose. Đặt SECRET_KEY là chuỗi ngẫu nhiên ít nhất 32 ký tự trước khi chạy:

```powershell
$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
docker compose up --build -d
```

Mở http://localhost:8000/client/ hoặc http://localhost:8000/admin/login. Cấu hình mặc định dùng thanh toán mô phỏng và cơ sở dữ liệu thật trong Docker. Không tự tạo tài khoản mẫu.

Để tạo quản trị viên lần đầu, đặt SUPERADMIN_BOOTSTRAP_MODE=create cùng SUPERADMIN_EMAIL và SUPERADMIN_PASSWORD mới dài ít nhất 12 ký tự; khởi động lại API, rồi chuyển chế độ về disabled. Không dùng mật khẩu mẫu.

## Chạy từng thành phần

Python 3.12 và Node.js 22. Sao chép backend/.env.example sang backend/.env, điền SECRET_KEY và URI MongoDB replica set. Các tệp .env thực tế không được đưa vào Git.

```powershell
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock
.venv/Scripts/python -m uvicorn app.main:app --reload
# Terminal khác, cùng thư mục và cấu hình:
.venv/Scripts/python worker.py
```

```powershell
cd apps/web-admin
npm ci
npm run dev
```

Web App dùng trên trình duyệt máy tính và điện thoại. Các cổng `/client/`, `/owner/` và `/admin/` dùng chung ứng dụng React. GPS cần HTTPS và quyền vị trí; trình duyệt có thể tạm ngừng khi khóa màn hình. Xem [phạm vi Web App](docs/WEB_APP_SCOPE.md).

## Kiểm tra

```powershell
cd backend
python -m pip install pytest pytest-asyncio
python -m pytest -q
# MongoDB replica set kiểm thử riêng, mặc định cổng 27028:
python verify_mongo.py
cd ..
node --test shared/tests/*.test.mjs
cd apps/web-admin
npm run build
```

Kiểm tra trình duyệt có fixture riêng: xem docs/RELEASE_READINESS.md. CI chạy kiểm thử API, giao dịch MongoDB thật, kiểm thử GPS dùng chung, build web và smoke container. CD chỉ chạy khi chọn workflow_dispatch với deploy=true và cấu hình GitHub Environment production.

## Triển khai và phạm vi ngoại tuyến

Dùng deploy/docker-compose.prod.yml và deploy/env/.env.production.example. Cần cấu hình HTTPS ở reverse proxy ngoài, SMTP, khóa ký giấy phép offline riêng và thông tin cổng thanh toán thật.

Gói offline hiện lưu nội dung POI, audio và ảnh tự lưu trữ có checksum, gắn tài khoản và giấy phép 7 ngày. Bản đồ nền, tạo tuyến đường mới và dịch vụ AI vẫn cần mạng. Chưa có bộ dữ liệu bản đồ offline được cấp kèm dự án.

Chi tiết thay đổi, điều kiện đưa cho người dùng và giới hạn kiểm chứng nằm trong [docs/RELEASE_READINESS.md](docs/RELEASE_READINESS.md).
