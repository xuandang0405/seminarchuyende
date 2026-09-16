# Version Lockfile & Dependency Baseline

Tài liệu này khóa các phiên bản công nghệ chính thức của dự án nhằm đảm bảo tính tương thích và ngăn ngừa xung đột phiên bản.

---

## 1. Backend Stack

| Thành phần | Phiên bản | Nguồn tài liệu & Ghi chú |
|---|---|---|
| **Python** | `3.12.3` | Phiên bản runtime đã xác minh trên máy chủ |
| **FastAPI** | `0.110.0+` (thực tế `0.141.1`) | Hỗ trợ Pydantic v2 và Lifespan context manager |
| **Pydantic** | `2.13.5` | Pydantic v2 cho Data Validation và Serialization |
| **PyMongo** | `4.18.1` | Tích hợp native `AsyncMongoClient` thay thế Motor |
| **Uvicorn** | `0.53.0` | ASGI Server với tiêu chuẩn chuẩn hóa |
| **Edge-TTS** | `7.2.8` | TTS Provider offline/online chất lượng cao |
| **PyJWT** | `2.14.0` | JWT Token generation và verification |
| **Passlib / Bcrypt** | `1.7.4 / 5.0.0` | Băm mật khẩu chuẩn bảo mật |
| **pytest / pytest-asyncio**| `9.1.1 / 1.4.0` | Khung kiểm thử tự động bất đồng bộ |

---

## 2. Web Admin & Owner Portal Stack (`apps/web-admin/`)

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| **Node.js** | `v24.21.0` | Runtime JavaScript đã xác minh trên máy chủ |
| **React** | `^18.3.1` hoặc `^19.0.0` | React core framework |
| **Vite** | `^5.4.0` | Công cụ build hiện đại, tốc độ cao |
| **TypeScript** | `^5.5.0` | Bật chế độ `strict: true` |
| **TanStack Query** | `^5.50.0` | Quản lý Server State, caching và auto-refetch |
| **React Router** | `^6.26.0` | Quản lý điều hướng Client-side |
| **React Hook Form + Zod** | `^7.52.0 / ^3.23.0` | Form handling và Schema validation |
| **Lucide React** | `^0.400.0` | Icon system nhất quán |
| **Tailwind CSS** | `^3.4.0` | Utility-first styling theo hệ thống token |

---

## 3. Mobile Tourist Client Stack (`apps/mobile/`)

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| **Expo SDK** | `~57.0.0` | Nền tảng phát triển React Native |
| **React Native** | `0.86.3` | Native runtime |
| **expo-location** | `~57.0.18` | Định vị GPS và Foreground/Background service |
| **expo-audio / expo-av** | `~16.0.8` | Phát audio đa ngôn ngữ và xử lý audio focus |
| **expo-camera** | `~57.0.5` | Quét mã QR POI |
| **expo-sqlite** | `~15.0.0` | Database SQLite lưu trữ metadata offline |
| **expo-file-system**| `~18.0.0` | Lưu trữ file MP3 và ảnh cục bộ |
| **Zustand** | `^4.5.0` | Quản lý client state (Player state, Locale) |
