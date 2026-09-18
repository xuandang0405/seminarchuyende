# Hướng Dẫn Triển Khai Hệ Thống TourVoice Quận 4 (Local -> Host Deployment Guide)

Tài liệu này hướng dẫn chi tiết quy trình đưa ứng dụng **Hệ thống Thuyết minh Du lịch Tự động Quận 4** từ môi trường phát triển cục bộ lên máy chủ VPS (đang thử nghiệm tại IP `1.55.58.251` và đích đến là domain `https://tour.quan4.vn`).

---

## 1. Bản Chất Lỗi Localhost & Kiến Trúc Same-Origin Được Lựa Chọn

### 1.1. Tại sao trước đây bị lỗi CORS / Private Network Access?
- Khi mở giao diện quản trị từ xa tại `http://1.55.58.251:8000/admin/`, file JavaScript chạy **trên trình duyệt của người dùng**.
- Mã nguồn cũ chứa dòng `const API_BASE = "http://localhost:8000/api/v1"`, khiến trình duyệt gửi request tới `localhost` (chính là máy tính cá nhân của người truy cập, nơi không hề có backend nào đang chạy).
- Cơ chế bảo mật trình duyệt (**Private Network Access & CORS**) đã chặn request này vì trang web công cộng (`http://1.55.58.251`) không được phép âm thầm gọi vào địa chỉ nội bộ (`loopback/localhost`) trong ngữ cảnh không an toàn (HTTP).

### 1.2. Giải pháp Kiến trúc Same-Origin (Ưu tiên số 1)
Thay vì bắt trình duyệt xử lý cross-origin phức tạp, toàn bộ hệ thống được gom về **cùng một Origin** qua Nginx:
```text
  [Người Dùng / Du Khách]
             |
             v (HTTP 80 / HTTPS 443)
       [Nginx Reverse Proxy]
             |
             +---> /api/v1/*   --> Proxy nội bộ tới FastAPI :8000 (giữ nguyên path)
             +---> /storage/*  --> Proxy nội bộ tới Static Media Storage :8000
             +---> /client/*   --> Giao diện Du khách
             +---> /admin/*    --> Cổng Quản trị CMS
```
- **Frontend** chỉ gọi relative path: `/api/v1/auth/login`.
- **Nginx** nhận request và chuyển tiếp cho FastAPI.
- **Trình duyệt** thấy Frontend và API cùng scheme/host/port nên **hoàn toàn không gặp lỗi CORS hay loopback blocked**.

---

## 2. Các Bước Triển Khai Lên Server VPS (Host)

### Bước 1: Đóng gói mã nguồn từ máy Local
Tại thư mục gốc dự án trên máy phát triển, chạy build guard để đảm bảo không còn `localhost`:
```bash
node scripts/assert-no-client-localhost.mjs
```

Tạo file nén đóng gói bản phát hành (loại bỏ thư mục rác, file `.env` cá nhân và git):
```bash
# Trên Linux/macOS hoặc Git Bash:
tar --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.venv' \
    --exclude='backend/.env' \
    -czf tourvoice_release.tar.gz \
    backend frontend apps deploy scripts
```

### Bước 2: Chuyển file lên VPS qua SCP
```bash
scp tourvoice_release.tar.gz root@1.55.58.251:/opt/
```

### Bước 3: Giải nén và thiết lập môi trường trên VPS
Đăng nhập vào VPS:
```bash
ssh root@1.55.58.251
```

Tạo cấu trúc thư mục chuẩn:
```bash
mkdir -p /opt/tour-guide/releases/release_$(date +%Y%m%d)
mkdir -p /opt/tour-guide/shared/storage
tar -xzf /opt/tourvoice_release.tar.gz -C /opt/tour-guide/releases/release_$(date +%Y%m%d)

# Tạo symlink thư mục hiện tại
ln -sfn /opt/tour-guide/releases/release_$(date +%Y%m%d) /opt/tour-guide/current
```

Cấu hình file môi trường sản xuất:
```bash
cp /opt/tour-guide/current/deploy/env/.env.production.example /opt/tour-guide/shared/.env
# Chỉnh sửa các secret (JWT_SECRET, Mongo URL nếu cần):
nano /opt/tour-guide/shared/.env
chmod 600 /opt/tour-guide/shared/.env

# Gắn link .env và storage vào bản release hiện tại:
ln -sf /opt/tour-guide/shared/.env /opt/tour-guide/current/backend/.env
ln -sfn /opt/tour-guide/shared/storage /opt/tour-guide/current/backend/storage
```

Cài đặt môi trường Python ảo cho backend:
```bash
cd /opt/tour-guide/current/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 4: Cấu hình Nginx Reverse Proxy
```bash
# Copy file cấu hình Nginx
cp /opt/tour-guide/current/deploy/nginx/tour-guide.conf /etc/nginx/sites-available/tour-guide.conf
ln -sf /etc/nginx/sites-available/tour-guide.conf /etc/nginx/sites-enabled/

# Kiểm tra cú pháp cấu hình Nginx
nginx -t

# Khởi động lại Nginx
systemctl reload nginx
```

### Bước 5: Kích hoạt Service Systemd cho FastAPI
```bash
cp /opt/tour-guide/current/deploy/systemd/tour-guide-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable tour-guide-api
systemctl restart tour-guide-api
```

---

## 3. Kiểm Thử Khói Tự Động (Smoke Test)

Sau khi dịch vụ khởi động, chạy script kiểm thử khói để xác thực toàn bộ hệ thống:
```bash
bash /opt/tour-guide/current/deploy/scripts/smoke-test.sh http://1.55.58.251
```

Script sẽ tự động xác minh 5 tiêu chí:
1. Endpoint `/api/v1/health` trả về HTTP 200.
2. Endpoint `/api/v1/map/config` trả về cấu hình bản đồ chuẩn Quận 4.
3. CORS Preflight `OPTIONS /api/v1/auth/login` phản hồi đầy đủ headers hợp lệ.
4. Giao diện du khách `/client/` tải thành công.
5. Mã nguồn `admin.js` không còn chứa chuỗi `http://localhost:8000`.

---

## 4. Quy Trình Khôi Phục Sự Cố (Rollback)

Nếu bản release mới gặp lỗi, chạy script rollback để chuyển tức thì về bản release liền trước:
```bash
bash /opt/tour-guide/current/deploy/scripts/rollback.sh
```

---

## 5. Nâng Cấp Lên Tên Miền Chính Thức & HTTPS (SSL/TLS)

Khi chủ dự án đã trỏ bản ghi DNS của tên miền (ví dụ: `tour.quan4.vn`) về IP `1.55.58.251`:
1. Mở cổng firewall 443:
   ```bash
   sudo ufw allow 443/tcp
   ```
2. Cài đặt chứng chỉ SSL miễn phí tự gia hạn qua Let's Encrypt Certbot:
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d tour.quan4.vn
   ```
3. Cập nhật `PUBLIC_WEB_URL` trong `/opt/tour-guide/shared/.env`:
   ```env
   PUBLIC_WEB_URL="https://tour.quan4.vn"
   COOKIE_SECURE=true
   ```
4. Khởi động lại backend:
   ```bash
   sudo systemctl restart tour-guide-api
   ```
