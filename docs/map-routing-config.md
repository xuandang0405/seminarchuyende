# Hướng Dẫn Cấu Hình Bản Đồ & Định Tuyến (Map & Routing Configuration Guide)

Tài liệu này hướng dẫn chi tiết các tham số cấu hình, biến môi trường và quy trình triển khai cho mô-đun Bản đồ & Tuyến đường Thực tế trong hệ thống Thuyết minh Du lịch Quận 4.

---

## 1. Biến Môi Trường Backend (.env)

Các tham số sau được định nghĩa trong `backend/app/core/config.py` và có thể ghi đè qua file `.env`:

```bash
# --- Bản đồ Số & Ranh giới Quận 4 ---
MAP_DISTRICT_4_MIN_LAT=10.7480
MAP_DISTRICT_4_MAX_LAT=10.7720
MAP_DISTRICT_4_MIN_LON=106.6900
MAP_DISTRICT_4_MAX_LON=106.7150
MAP_CENTER_LAT=10.7635
MAP_CENTER_LON=106.7042
MAP_DEFAULT_ZOOM=15

# --- Tile Server CartoDB Dark Matter ---
MAP_TILE_URL="https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png"
MAP_ATTRIBUTION="&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors &copy; <a href=\"https://carto.com/attributions\">CARTO</a>"

# --- OSRM Routing Engine & Caching ---
# Mặc định sử dụng OSRM v5 public server:
ROUTING_PROVIDER_URL="https://router.project-osrm.org"
# Thời gian timeout khi gọi routing (giây):
ROUTING_TIMEOUT_SECONDS=3.0
# Thời gian tồn tại của bản ghi cache tuyến đường (giờ):
ROUTING_CACHE_TTL_HOURS=24
```

---

## 2. API Cấu Hình Động cho Frontend (/api/v1/map/config)

Frontend Web và Mobile không bao giờ hardcode ranh giới hoặc tile URL mà luôn gọi endpoint cấu hình để lấy thông tin đồng bộ:

```http
GET /api/v1/map/config
```

**Mẫu Phản Hồi:**
```json
{
  "center": {
    "latitude": 10.7635,
    "longitude": 106.7042
  },
  "default_zoom": 15,
  "bounds": {
    "min_latitude": 10.748,
    "max_latitude": 10.772,
    "min_longitude": 106.69,
    "max_longitude": 106.715
  },
  "tile_url": "https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png",
  "attribution": "&copy; OpenStreetMap contributors &copy; CARTO",
  "routing_provider": "osrm",
  "supported_travel_modes": ["walking", "driving"]
}
```

---

## 3. MongoDB Indexes Bắt Buộc

Khi khởi động hệ thống (`backend/app/db/indexes.py`), các index sau sẽ tự động được khởi tạo:

1. **Collection `pois`**:
   - `2dsphere`: Index trên trường `location` hỗ trợ tìm kiếm không gian `$geoNear`, `$geoWithin`, `$nearSphere`.
   - `compound`: `{ "is_active": 1, "category": 1 }` hỗ trợ lọc theo danh mục nhanh chóng.
   - `text`: Index đa trường `{ "name": "text", "description": "text", "address": "text" }` với `default_language="none"`.

2. **Collection `route_cache`**:
   - `unique`: Index `{ "fingerprint": 1 }` đảm bảo tính duy nhất của mã băm tuyến đường.
   - `TTL Index`: `{ "expires_at": 1 }` với `expireAfterSeconds: 0` giúp MongoDB tự động giải phóng bộ nhớ khi bản ghi hết hạn (24h).
   - `compound`: `{ "mode": 1, "created_at": -1 }` tối ưu hóa thống kê phân tích.

---

## 4. Cách Thiết Lập OSRM Cục Bộ Bằng Docker (Tùy Chọn)

Nếu muốn tự host máy chủ định tuyến OSRM để hoàn toàn không phụ thuộc internet:

```bash
# 1. Tải dữ liệu OSM khu vực Việt Nam / TP.HCM
curl -O https://download.geofabrik.de/asia/vietnam-latest.osm.pbf

# 2. Tiền xử lý dữ liệu với profile đi bộ (foot)
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/vietnam-latest.osm.pbf
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/vietnam-latest.osrm
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/vietnam-latest.osrm

# 3. Khởi chạy OSRM Server tại cổng 5000
docker run -t -i -p 5000:5000 -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/vietnam-latest.osrm

# 4. Cập nhật file .env của backend
ROUTING_PROVIDER_URL="http://localhost:5000"
```
