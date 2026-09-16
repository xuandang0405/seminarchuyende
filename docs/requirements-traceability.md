# Requirements Traceability Matrix (RTM) — Focused Step-Level Traceability

Tài liệu ma trận truy vết yêu cầu phần mềm mở rộng. Ánh xạ chi tiết từ Use Case, hồ sơ đặc tả Focused Use Case, các bước và nhánh sự kiện (Flow/Step ID), quy tắc nghiệp vụ (`BR_ID`), sơ đồ Sequence (`SD*`), Activity (`AD*`), giao diện (Screen), API Endpoint, Service/Engine, Cơ sở dữ liệu và bằng chứng kiểm thử tự động.

---

## Bảng Truy Vết Yêu Cầu Chi Tiết (Focused Traceability)

| UC_ID | Hồ Sơ Đặc Tả | Flow / Step / Branch ID | BR_ID | Sơ Đồ SD / AD | Màn Hình UI | Endpoint | Service / Engine | Collection / DB | Bằng Chứng Test Tự Động | Trạng Thái |
|---|---|---|---|---|---|---|---|---|---|---|
| **T01** | `T01-map.md` | `T01.B1–B4` | — | SD01, AD01 | `MapScreen.js` | `GET /api/v1/pois` | `PoiService` | `POI` | `test_poi_full_slice.py` | **HOÀN THÀNH** |
| **T02** | `T02-gps.md` | `T02.B1–B3` | `BR-GEO-01` | SD04, AD04 | `MapScreen.js` | Native GPS API | `LocationService.js` | Native Location | `mobile/tests/geofence.test.js` | **HOÀN THÀNH** |
| **T03** | `T03-search.md` | `T03.B1–B3` | — | SD01, AD01 | `MapScreen.js` | `GET /api/v1/pois?search=...` | `PoiService` | `POI` | `test_poi_full_slice.py` | **HOÀN THÀNH** |
| **T04** | `T04-nearby.md` | `T04.B1–B3` | `BR-GEO-01` | SD04, AD04 | `MapScreen.js` | `GET /api/v1/pois/nearby` | `PoiService` | `POI` (2dsphere) | `test_api.py::test_list_pois_standard` | **HOÀN THÀNH** |
| **T05** | `T05-detail.md` | `T05.B1–B4` | `BR-POI-01` | SD01, AD01 | `POIDetailModal.js` | `GET /api/v1/pois/{id}` | `PoiService` | `POI`, `poi_localizations` | `test_poi_full_slice.py::test_get_poi_detail` | **HOÀN THÀNH** |
| **T06** | `T06-menu.md` | `T06.B1–B3` | — | — | `POIDetailModal.js` | `GET /api/v1/pois/{id}/menu` | `MenuService` | `MenuItem` | `test_moderation.py::test_idor_protection_for_menu` | **HOÀN THÀNH** |
| **T07** | `T07-lang.md` | `T07.B1–B3` | `BR-AUDIO-02` | SD01, AD01 | `SettingsModal.js` | Client state / API | `NarrationController.js` | Client preferences | `test_poi_full_slice.py` | **HOÀN THÀNH** |
| **T08** | `T08-T09-T10-audio-narration.md` | `T08.B1–B7`, `A1` | `BR-AUDIO-01, 03` | SD04, AD16 | `POIDetailModal.js` | Streaming / Storage | `NarrationController.js` | `poi_localizations` | `mobile/tests/geofence.test.js` | **HOÀN THÀNH** |
| **T09** | `T08-T09-T10-audio-narration.md` | `T09.B1–B5`, `A2` | `BR-GEO-01, 02` | SD04, AD04, AD16 | Background / Map | GPS Event Stream | `GeofenceEngine.js` | Local cooldowns | `mobile/tests/geofence.test.js` (6/6 passed) | **HOÀN THÀNH** |
| **T10** | `T08-T09-T10-audio-narration.md` | `T10.B1–B3` | `BR-AUDIO-01` | AD16 | `AudioPlayerBar.js` | `expo-av` controls | `NarrationController.js` | Playback status | `mobile/tests/geofence.test.js` | **HOÀN THÀNH** |
| **T11** | `T11-scan-qr.md` | `T11.B1–B7`, `A1, E1–E5` | `BR-QR-01, 02` | SD05, AD05, AD16 | `QRScanScreen.js` | `GET /api/v1/qr/{code}` | `QRService` | `qr_codes`, `POI` | `test_api.py::test_qr_resolution_standard` | **HOÀN THÀNH** |
| **T12** | `T12-T13-walking-tours.md` | `T12.B1–B3` | `BR-TOUR-01` | SD14, AD14 | `TourModal.js` | `GET /api/v1/tours` | `TourService` | `tours` | `test_api.py::test_tours_listing` | **HOÀN THÀNH** |
| **T13** | `T12-T13-walking-tours.md` | `T13.B1–B6`, `A1` | `BR-TOUR-01, BR-CONSENT-01` | SD14, AD14 | `MapScreen.js` | Polyline / Session | `TourSessionService.js` | AsyncStorage active tour | `mobile/src/services/TourSessionService.js` | **HOÀN THÀNH** |
| **N01** | `N01-N02-narration-subflows.md` | `N01.B1–B6` | `BR-AUDIO-01, 02` | AD16 | `AudioPlayerBar.js` | Single Audio Driver | `NarrationController.js` | State machine | `mobile/tests/geofence.test.js` | **HOÀN THÀNH** |
| **N02** | `N01-N02-narration-subflows.md` | `N02.B1–B3`, `A1` | `BR-JOB-01, BR-AUDIO-03` | SD07, AD07 | Detail / On-demand | `POST /api/v1/audio/tts` | `TTSService` (Edge-TTS) | `audio_tasks` | `test_poi_full_slice.py` | **HOÀN THÀNH** |
| **F01** | `F01-map-mode.md` | `F01.B1–B2` | — | SD06, AD06 | `OfflineScreen.js` | Client Map Switch | `OfflinePackService.js` | AsyncStorage | `mobile/src/screens/OfflineScreen.js` | **HOÀN THÀNH** |
| **F02** | `F02-download-offline-pack.md` | `F02.B1–B7`, `A1, E1–E2` | `BR-OFFLINE-01` | SD06, AD06 | `OfflineScreen.js` | `GET /api/v1/pois`, `/tours` | `OfflinePackService.js` | `tourvoice_offline_manifest` | `mobile/src/screens/OfflineScreen.js` | **HOÀN THÀNH** |
| **F03** | `F02-download-offline-pack.md` | `F02.A1` | `BR-OFFLINE-01` | SD06, AD06 | `OfflineScreen.js` | Re-sync bundles | `OfflinePackService.js` | Local storage | `mobile/src/screens/OfflineScreen.js` | **HOÀN THÀNH** |
| **F04** | `F02-download-offline-pack.md` | `F02.A1` | `BR-OFFLINE-01` | SD06, AD06 | `OfflineScreen.js` | Repair / Re-download | `OfflinePackService.js` | Local storage | `mobile/src/screens/OfflineScreen.js` | **HOÀN THÀNH** |
| **F05** | `F02-download-offline-pack.md` | `F02.A2` | `BR-OFFLINE-02` | SD06, AD06 | `OfflineScreen.js` | Remove Pack | `OfflinePackService.js` | Local storage | `mobile/src/screens/OfflineScreen.js` | **HOÀN THÀNH** |
| **F06** | `F02-download-offline-pack.md` | `F06.B1–B3` | `BR-AUDIO-03` | SD06, AD06 | FlightMode Map | Local cache reader | `AudioSourceResolver.js` | Cached manifest | `mobile/src/services/AudioSourceResolver.js` | **HOÀN THÀNH** |
| **F07** | `F07-sync.md` | `F07.B1–B4` | `BR-EVENT-01` | SD01, AD11 | App Resume | `POST /api/v1/analytics/events/batch` | `AnalyticsOutbox.js` | `analytics_events` | `test_analytics.py::test_analytics_consent_and_batch_ingestion` | **HOÀN THÀNH** |
| **F08** | `F08-manage-analytics-consent.md` | `F08.B1–B4`, `A1` | `BR-CONSENT-01` | SD11, AD11 | `SettingsModal.js` | Client Consent Toggle | `AnalyticsOutbox.js` | `tourvoice_analytics_consent` | `test_analytics.py::test_analytics_consent_and_batch_ingestion` | **HOÀN THÀNH** |
| **U01** | `U01-login.md` | `U01.B1–B6`, `A1, E1–E4` | `BR-AUTH-01` | SD02, AD02 | `Login.tsx` | `POST /api/v1/admin/auth/login` | `AuthService` | `admin_users`, `roles`, `auth_sessions` | `test_auth_rbac.py::test_login_success` | **HOÀN THÀNH** |
| **U02** | `U02-logout.md` | `U02.B1–B3` | `BR-AUTH-01` | — | Sidebar Header | `POST /api/v1/admin/auth/logout` | `AuthService` | `auth_sessions` | `test_auth_rbac.py` | **HOÀN THÀNH** |
| **U03** | `U03-change-pwd.md` | `U03.B1–B4` | `BR-AUTH-01` | — | Profile Settings | `POST /api/v1/admin/auth/change-password` | `AuthService` | `admin_users` | `test_auth_rbac.py` | **HOÀN THÀNH** |
| **O01** | `O01-register-owner.md` | `O01.B1–B6`, `E1–E2` | `BR-AUTH-01, BR-OWNER-01` | SD08, AD08 | `Login.tsx` (Register) | `POST /api/v1/admin/auth/register-owner` | `AuthService` | `poi_owner_registrations` | `test_auth_rbac.py::test_owner_registration_flow` | **HOÀN THÀNH** |
| **O02** | `O02-reg-status.md` | `O02.B1–B3` | `BR-OWNER-01` | SD08, AD08 | `OwnerPortal.tsx` | `GET /api/v1/owner/registration` | `OwnerService` | `poi_owner_registrations` | `test_auth_rbac.py` | **HOÀN THÀNH** |
| **O03** | `O03-owner-pois.md` | `O03.B1–B3` | `BR-OWNER-01` | SD09, AD09 | `OwnerPortal.tsx` | `GET /api/v1/owner/pois` | `OwnerService` | `POI` (owner scoped) | `test_moderation.py::test_owner_submission_and_admin_review` | **HOÀN THÀNH** |
| **O04** | `O04-edit-draft.md` | `O04.B1–B4` | `BR-OWNER-01` | SD09, AD09 | `OwnerPortal.tsx` | Form draft | `OwnerService` | `poi_submissions` | `test_moderation.py` | **HOÀN THÀNH** |
| **O05** | `O05-submit-poi-content.md` | `O05.B1–B6`, `E1–E2` | `BR-OWNER-01, BR-REVIEW-02` | SD09, AD09 | `OwnerPortal.tsx` | `POST /api/v1/owner/submissions` | `OwnerService` | `poi_submissions` | `test_moderation.py::test_owner_submission_and_admin_review` | **HOÀN THÀNH** |
| **O06** | `O06-submission-result.md` | `O06.B1–B3` | `BR-OWNER-01` | SD09, AD09 | `OwnerPortal.tsx` | `GET /api/v1/owner/submissions` | `OwnerService` | `poi_submissions` | `test_moderation.py` | **HOÀN THÀNH** |
| **O07** | `O07-notifications.md` | `O07.B1–B3` | `BR-OWNER-01` | SD10, AD10 | `OwnerPortal.tsx` | `GET /api/v1/owner/notifications` | `OwnerService` | `owner_notifications` | `test_moderation.py` | **HOÀN THÀNH** |
| **O08** | `O08-mark-read.md` | `O08.B1–B2` | `BR-OWNER-01` | — | NotificationItem | `PATCH /api/v1/owner/notifications/{id}/read` | `OwnerService` | `owner_notifications` | `test_moderation.py` | **HOÀN THÀNH** |
| **O09** | `O09-manage-menu.md` | `O09.B1–B4` | `BR-OWNER-01` | — | `OwnerPortal.tsx` | `POST /api/v1/owner/menu` | `MenuService` | `MenuItem` (IDOR check) | `test_moderation.py::test_idor_protection_for_menu` | **HOÀN THÀNH** |
| **O10** | `O10-owner-statistics.md` | `O10.B1–B4`, `E1` | `BR-OWNER-01, BR-METRIC-01` | SD13, AD13 | `OwnerPortal.tsx` | `GET /api/v1/owner/analytics` | `AnalyticsService` | `analytics_poi_daily_metrics` | `test_analytics.py` | **HOÀN THÀNH** |
| **C01** | `C01-C02-manage-poi.md` | `C01.B1–B7`, `A1, E1–E3` | `BR-POI-01, BR-IDEM-01` | SD03, AD03 | `POIList.tsx` | `POST /api/v1/admin/pois` | `PoiAdminService` | `POI` | `test_poi_full_slice.py::test_poi_creation_and_concurrency_control` | **HOÀN THÀNH** |
| **C02** | `C01-C02-manage-poi.md` | `C02.B1–B5`, `E2` | `BR-VERSION-01` | SD03, AD03 | `POIList.tsx` | `PATCH /api/v1/admin/pois/{id}` | `PoiAdminService` | `POI` | `test_poi_full_slice.py::test_poi_creation_and_concurrency_control` | **HOÀN THÀNH** |
| **C03** | `C03-delete-poi.md` | `C03.B1–B3` | — | — | `POIList.tsx` | `DELETE /api/v1/admin/pois/{id}` | `PoiAdminService` | `POI` (`deleted_at`) | `test_poi_full_slice.py` | **HOÀN THÀNH** |
| **C04** | `C01-C02-manage-poi.md` | `C04.B1–B3`, `A1` | `BR-POI-01` | SD03, AD03 | `POIList.tsx` | `POST /api/v1/admin/pois/{id}/toggle-active` | `PoiAdminService` | `POI` (`is_active`) | `test_poi_full_slice.py::test_publication_readiness_gate` | **HOÀN THÀNH** |
| **C05** | `C05-admin-menu.md` | `C05.B1–B3` | — | — | `POIList.tsx` | `GET /api/v1/pois/{id}/menu` | `MenuService` | `MenuItem` | `test_moderation.py` | **HOÀN THÀNH** |
| **C06** | `C06-review-registration.md` | `C06.B1–B6`, `A1, E1` | `BR-REVIEW-01, BR-OWNER-01` | SD10, AD10 | `Moderation.tsx` | `POST /api/v1/admin/moderation/registrations/{id}` | `ModerationService` | `poi_owner_registrations`, `admin_users` | `test_auth_rbac.py::test_owner_registration_flow` | **HOÀN THÀNH** |
| **C07** | `C07-review-submission.md` | `C07.B1–B6`, `A1–A2, E1–E5` | `BR-REVIEW-01, BR-REVIEW-02` | SD10, AD10 | `Moderation.tsx` | `POST /api/v1/admin/moderation/submissions/{id}` | `ModerationService` | `poi_submissions`, `POI` | `test_moderation.py::test_owner_submission_and_admin_review` | **HOÀN THÀNH** |
| **C08** | `C08-edit-translation.md` | `C08.B1–B3` | — | — | `POIList.tsx` | `PATCH /api/v1/admin/pois/{id}/localizations/{lang}` | `PoiAdminService` | `poi_localizations` | `test_poi_full_slice.py` | **HOÀN THÀNH** |
| **C09** | `C09-auto-translate.md` | `C09.B1–B3` | — | SD07, AD07 | `POIList.tsx` | `POST /api/v1/admin/pois/{id}/translate` | `TranslationService` | `poi_localizations` | `test_poi_full_slice.py` | **HOÀN THÀNH** |
| **C10** | `C10-upload-mp3.md` | `C10.B1–B3` | — | — | `POIList.tsx` | `POST /api/v1/audio/upload` | `StorageService` | `poi_localizations` | `test_api.py` | **HOÀN THÀNH** |
| **C11** | `C11-C13-tts-audio-tasks.md` | `C11.B1–B6`, `E1` | `BR-JOB-01, BR-POI-01` | SD07, AD07 | `POIList.tsx` | `POST /api/v1/audio/tts` | `TTSService` (Edge-TTS) | `audio_tasks`, `poi_localizations` | `test_poi_full_slice.py` | **HOÀN THÀNH** |
| **C12** | `C11-C13-tts-audio-tasks.md` | `C12.B1–B3` | `BR-JOB-01` | SD07, AD07 | `POIList.tsx` | `GET /api/v1/audio/tasks/{id}` | `AudioRepo` | `audio_tasks` | `test_api.py` | **HOÀN THÀNH** |
| **C13** | `C11-C13-tts-audio-tasks.md` | `C13.B1–B3` | `BR-JOB-01` | SD07, AD07 | `POIList.tsx` | Task control | `AudioRepo` | `audio_tasks` | `test_api.py` | **HOÀN THÀNH** |
| **C14** | `C14-ai-description.md` | `C14.B1–B5`, `A1, E1–E2` | `BR-AI-01, BR-AUTH-01` | SD15, AD15 | `POIList.tsx` | `POST /api/v1/ai/generate-description` | `AIService` | `ai_usage_limits` | `test_api.py` | **HOÀN THÀNH** |
| **C15** | `C15-manage-tours.md` | `C15.B1–B4` | `BR-TOUR-01` | — | `Tours.tsx` | `CRUD /api/v1/admin/tours` | `TourService` | `tours` | `test_api.py::test_tours_listing` | **HOÀN THÀNH** |
| **C16** | `C16-manage-qr.md` | `C16.B1–B4` | `BR-QR-01` | — | `QRCodes.tsx` | `CRUD /api/v1/admin/qr-codes` | `QRService` | `qr_codes` | `test_api.py::test_qr_resolution_standard` | **HOÀN THÀNH** |
| **S01** | `S01-manage-users.md` | `S01.B1–B3` | `BR-AUTH-01` | — | Admin Users Table | `GET /api/v1/admin/users` | `AuthService` | `admin_users` | `test_auth_rbac.py` | **HOÀN THÀNH** |
| **S02** | `S02-manage-roles.md` | `S02.B1–B2` | `BR-AUTH-01` | — | SuperAdmin Roles | `GET /api/v1/admin/roles` | `AuthService` | `roles` | `test_auth_rbac.py` | **HOÀN THÀNH** |
| **S03** | `S03-assign-permissions.md`| `S03.B1–B3` | `BR-AUTH-01` | — | SuperAdmin Modal | Role permission map | `AuthService` | `roles` | `test_auth_rbac.py` | **HOÀN THÀNH** |
| **S04** | `S04-audit-logs.md` | `S04.B1–B3` | — | — | `AuditLogs.tsx` | `GET /api/v1/admin/audit-logs` | `BaseRepository` | `audit_logs` | `test_api.py` | **HOÀN THÀNH** |
| **S05** | `S05-S07-analytics-dashboard.md`| `S05.B1–B4`, `E1` | `BR-AGG-01` | SD12, SD13, AD12 | `Dashboard.tsx` | `GET /api/v1/analytics/dashboard` | `AnalyticsService` | `analytics_daily_metrics` | `test_analytics.py::test_analytics_dashboard` | **HOÀN THÀNH** |
| **S06** | `S05-S07-analytics-dashboard.md`| `S06.B1–B2` | `BR-METRIC-01` | SD13, AD13 | `Dashboard.tsx` | `GET /api/v1/analytics/dashboard` | `AnalyticsService` | `analytics_poi_daily_metrics` | `test_analytics.py::test_analytics_dashboard` | **HOÀN THÀNH** |
| **S07** | `S05-S07-analytics-dashboard.md`| `S07.B1–B3` | `BR-METRIC-01` | SD13, AD13 | `Dashboard.tsx` | `GET /api/v1/analytics/dashboard` | `AnalyticsService` | `analytics_poi_daily_metrics` | `test_analytics.py::test_analytics_dashboard` | **HOÀN THÀNH** |
| **S08** | `S08-routes-stats.md` | `S08.B1–B2` | `BR-CONSENT-01` | — | Route Analytics | Analytics query | `AnalyticsService` | `analytics_sessions` | `test_analytics.py` | **HOÀN THÀNH** |
| **S09** | `S09-heatmap.md` | `S09.B1–B2` | `BR-CONSENT-01` | — | Heatmap Map | Spatial aggregation | `AnalyticsService` | `analytics_events` | `test_analytics.py` | **HOÀN THÀNH** |
| **S10** | `S10-export-reports.md` | — | — | — | Export Modal | Backlog P | — | — | — | *Proposal Backlog* |
| **S11** | `S11-runtime-health.md` | `S11.B1–B2` | — | — | Health Dashboard | `GET /health/live`, `/ready` | HealthCheck | Runtime state | `test_api.py::test_health_check` | **HOÀN THÀNH** |
| **S12** | `S12-system-config.md` | — | — | — | Admin Settings | Backlog P | — | — | — | *Proposal Backlog* |
| **S13** | `S13-data-backup.md` | — | — | — | Backup Utility | Backlog P | — | — | — | *Proposal Backlog* |
