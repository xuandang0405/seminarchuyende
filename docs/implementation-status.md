# Implementation Status & Milestones Tracking

Tài liệu này theo dõi tiến độ triển khai thực tế của dự án theo 7 giai đoạn (Phase A đến Phase G) và các bằng chứng kiểm thử thực tế.

---

## Tiến độ theo Giai đoạn

| Giai đoạn | Nội dung chính | Trạng thái | Bằng chứng kiểm tra thực tế |
|---|---|---|---|
| **Phase A** | Khóa hợp đồng, phân tích gap, tạo toàn bộ hồ sơ kỹ thuật RTM, Data Dictionary, Decisions | **HOÀN THÀNH** | Đã tạo đủ 8 tài liệu trong thư mục `docs/` |
| **Phase B** | Dựng nền tảng Monorepo, PyMongo Async, cấu hình 28 collections, seed dữ liệu, full slice POI API + Web + Mobile | **HOÀN THÀNH** | `init_db.py`, `indexes.py`, `seed.py` hoàn thiện; 17/17 tests pytest passed |
| **Phase C** | Bản dịch, Upload MP3, Edge-TTS Pipeline, Audio Tasks bền vững, Readiness Gate | **HOÀN THÀNH** | `tts_service.py` tích hợp `edge-tts 7.2.8`, `test_publication_readiness_gate` passed |
| **Phase D** | Mobile Geofence, Unified Narration, QR Scanner, Tour, Offline Pack Service | **HOÀN THÀNH** | 6/6 tests unit Node `geofence.test.js` passed; UI Modal, CameraView, AudioPlayerBar tích hợp |
| **Phase E** | Owner Registration, Submissions, Admin Review/Moderation, Audit Logs, IDOR Protection | **HOÀN THÀNH** | `test_owner_registration_flow`, `test_owner_submission_and_admin_review`, `test_idor_protection_for_menu` passed |
| **Phase F** | Analytics Consent (F08), Event Outbox, Hourly/Daily Aggregations, Dashboard | **HOÀN THÀNH** | `test_analytics_consent_and_batch_ingestion`, `test_analytics_dashboard` passed |
| **Phase G** | Nghiệm thu, Web Admin build, Mobile bundle, Docker Compose, OpenAPI contract | **HOÀN THÀNH** | `npm run build` web-admin passed (vite 2.69s); `openapi.json` 81.3KB; `docker-compose.yml` |
| **Phase H** | UPDATE_PROMPT_LOGIN_GOOGLE_SECURITY: Google OIDC, Session Rotation Cookie, Route Guard, Password Recovery, Diagrams | **HOÀN THÀNH** | 27/27 tests pytest passed; `test_auth_google_security.py` 10/10 passed; Web Admin build 0 errors |

---

## Chi tiết Bằng Chứng Kiểm Tra Tự Động

### 1. Backend Pytest Suite (Python 3.12 / pytest 9.1.1)
```text
tests/test_analytics.py::test_analytics_consent_and_batch_ingestion PASSED
tests/test_analytics.py::test_analytics_dashboard PASSED
tests/test_api.py::test_health_check PASSED
tests/test_api.py::test_admin_login PASSED
tests/test_api.py::test_list_pois_standard PASSED
tests/test_api.py::test_qr_resolution_standard PASSED
tests/test_api.py::test_tours_listing PASSED
tests/test_auth_google_security.py::test_1_login_credentials_and_passwordless PASSED
tests/test_auth_google_security.py::test_2_unauthenticated_and_privilege_escalation PASSED
tests/test_auth_google_security.py::test_3_refresh_token_rotation_and_reuse_detection PASSED
tests/test_auth_google_security.py::test_4_logout_and_logout_all PASSED
tests/test_auth_google_security.py::test_5_google_oauth_anti_automerge PASSED
tests/test_auth_google_security.py::test_6_google_oauth_new_user_role_assignment PASSED
tests/test_auth_google_security.py::test_7_google_account_linking_flow PASSED
tests/test_auth_google_security.py::test_8_password_recovery_flow PASSED
tests/test_auth_google_security.py::test_9_active_sessions_management PASSED
tests/test_auth_google_security.py::test_10_public_endpoints_unrestricted PASSED
tests/test_auth_rbac.py::test_login_success PASSED
tests/test_auth_rbac.py::test_login_invalid_password PASSED
tests/test_auth_rbac.py::test_owner_registration_flow PASSED
tests/test_auth_rbac.py::test_refresh_token_rotation PASSED
tests/test_moderation.py::test_owner_submission_and_admin_review PASSED
tests/test_moderation.py::test_idor_protection_for_menu PASSED
tests/test_poi_full_slice.py::test_get_public_pois PASSED
tests/test_poi_full_slice.py::test_get_poi_detail PASSED
tests/test_poi_full_slice.py::test_poi_creation_and_concurrency_control PASSED
tests/test_poi_full_slice.py::test_publication_readiness_gate PASSED

============================= 27 passed in 21.46s =============================
```

### 2. Mobile Geofence Engine Suite (Node.js Test Runner)
```text
✔ calculateDistanceMeters: accurate Haversine calculation (1.79ms)
✔ GeofenceEngine: ignores inaccurate GPS samples (> 35m accuracy) (0.34ms)
✔ GeofenceEngine: Debounce requires >= 3s presence before triggering (0.20ms)
✔ GeofenceEngine: Cooldown prevents repeated triggers for 5 minutes after playback (0.22ms)
✔ GeofenceEngine: Priority sorting selects higher audio_priority POI (0.26ms)
✔ GeofenceEngine: Stop suppression prevents re-trigger until user exits zone (0.23ms)
ℹ tests 6
ℹ pass 6
ℹ fail 0
```

### 3. Web Admin Production Build (Vite 5.4.21 / TypeScript 5.6.3)
```text
> tsc && vite build
vite v5.4.21 building for production...
transforming...
✓ 1629 modules transformed.
rendering chunks...
dist/index.html                   0.83 kB │ gzip:  0.50 kB
dist/assets/index-Bozr5r_J.css   21.17 kB │ gzip:  4.63 kB
dist/assets/index-cfDcdDkA.js   261.21 kB │ gzip: 76.10 kB
✓ built in 2.69s
```
