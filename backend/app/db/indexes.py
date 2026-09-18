"""Idempotent index creation script for all 28 collections.

Can be run multiple times safely on fresh or existing MongoDB databases.
"""

import logging
from pymongo.asynchronous.database import AsyncDatabase
from app.db.collections import (
    COLLECTION_POI,
    COLLECTION_POI_LOCALIZATIONS,
    COLLECTION_MENU_ITEM,
    COLLECTION_ROLES,
    COLLECTION_ADMIN_USERS,
    COLLECTION_POI_OWNER_REGISTRATIONS,
    COLLECTION_POI_SUBMISSIONS,
    COLLECTION_OWNER_NOTIFICATIONS,
    COLLECTION_AUDIT_LOGS,
    COLLECTION_AUDIO_TASKS,
    COLLECTION_AI_USAGE_LIMITS,
    COLLECTION_LOCALIZATION_RATE_LIMITS,
    COLLECTION_UI_TRANSLATION_BUNDLES,
    COLLECTION_ANALYTICS_DEVICES,
    COLLECTION_ANALYTICS_SESSIONS,
    COLLECTION_ANALYTICS_EVENTS,
    COLLECTION_ANALYTICS_POI_DAILY_METRICS,
    COLLECTION_ANALYTICS_DAILY_METRICS,
    COLLECTION_ANALYTICS_HOURLY_METRICS,
    COLLECTION_ANALYTICS_AGGREGATION_JOBS,
    COLLECTION_RUNTIME_LOCATION_HOURLY,
    COLLECTION_TOURS,
    COLLECTION_QR_CODES,
    COLLECTION_AUTH_SESSIONS,
    COLLECTION_IDEMPOTENCY_KEYS,
    COLLECTION_OFFLINE_PACK_MANIFESTS,
    COLLECTION_SCHEMA_MIGRATIONS,
    COLLECTION_AUTH_IDENTITIES,
    COLLECTION_AUTH_ACTION_TOKENS,
    COLLECTION_OAUTH_TRANSACTIONS,
    COLLECTION_GUEST_SESSIONS,
    COLLECTION_TRIAL_USAGE,
    COLLECTION_PLAYBACK_GRANTS,
    COLLECTION_ORDERS,
    COLLECTION_PAYMENT_ATTEMPTS,
    COLLECTION_PAYMENT_EVENTS,
    COLLECTION_TOUR_ENTITLEMENTS,
    COLLECTION_ROUTE_CACHE,
    COLLECTION_TOUR_SESSIONS,
)

logger = logging.getLogger("uvicorn")


async def create_all_indexes(db: AsyncDatabase):
    """Creates all required compound, unique, 2dsphere and TTL indexes idempotently."""
    logger.info("Starting idempotent index creation for collections...")

    try:
        # 1. roles: unique roles.name
        await db[COLLECTION_ROLES].create_index(
            [("name", 1)],
            unique=True,
            name="uq_roles_name"
        )

        # 2. admin_users: unique email (lowercase normalized)
        await db[COLLECTION_ADMIN_USERS].create_index(
            [("email", 1)],
            unique=True,
            name="uq_admin_users_email"
        )
        await db[COLLECTION_ADMIN_USERS].create_index(
            [("role", 1), ("is_active", 1)],
            name="idx_admin_users_role_active"
        )

        # 3. POI: 2dsphere on location, ownership, active status
        await db[COLLECTION_POI].create_index(
            [("location", "2dsphere")],
            name="idx_poi_location_2dsphere"
        )
        await db[COLLECTION_POI].create_index(
            [("is_active", 1), ("deleted_at", 1)],
            name="idx_poi_public_query"
        )
        await db[COLLECTION_POI].create_index(
            [("owner_id", 1), ("deleted_at", 1)],
            name="idx_poi_owner_query"
        )
        await db[COLLECTION_POI].create_index(
            [("category", 1), ("is_active", 1)],
            name="idx_poi_category_active"
        )
        await db[COLLECTION_POI].create_index(
            [("name", "text"), ("address", "text"), ("description", "text")],
            default_language="none",
            name="idx_poi_text_search"
        )

        # 4. poi_localizations: unique (poi_id, lang)
        await db[COLLECTION_POI_LOCALIZATIONS].create_index(
            [("poi_id", 1), ("lang", 1)],
            unique=True,
            name="uq_poi_localizations_poi_lang"
        )

        # 5. MenuItem: query by poi_id and active status
        await db[COLLECTION_MENU_ITEM].create_index(
            [("poi_id", 1), ("is_active", 1), ("deleted_at", 1)],
            name="idx_menu_item_poi_active"
        )

        # 6. poi_owner_registrations: query pending registrations
        await db[COLLECTION_POI_OWNER_REGISTRATIONS].create_index(
            [("status", 1), ("submitted_at", -1)],
            name="idx_owner_reg_status_date"
        )
        await db[COLLECTION_POI_OWNER_REGISTRATIONS].create_index(
            [("user_id", 1)],
            name="idx_owner_reg_user_id"
        )

        # 7. poi_submissions: query by owner_id, status, created_at
        await db[COLLECTION_POI_SUBMISSIONS].create_index(
            [("owner_id", 1), ("status", 1), ("created_at", -1)],
            name="idx_submissions_owner_status_date"
        )
        await db[COLLECTION_POI_SUBMISSIONS].create_index(
            [("status", 1), ("created_at", -1)],
            name="idx_submissions_status_date"
        )

        # 8. owner_notifications: query by owner_id and is_read
        await db[COLLECTION_OWNER_NOTIFICATIONS].create_index(
            [("owner_id", 1), ("is_read", 1), ("created_at", -1)],
            name="idx_owner_notifs_owner_read"
        )

        # 9. audit_logs: timestamp query, user query
        await db[COLLECTION_AUDIT_LOGS].create_index(
            [("timestamp", -1)],
            name="idx_audit_logs_timestamp"
        )
        await db[COLLECTION_AUDIT_LOGS].create_index(
            [("user_id", 1), ("timestamp", -1)],
            name="idx_audit_logs_user_date"
        )

        # 10. audio_tasks: query status, lease, and TTL on expires_at
        await db[COLLECTION_AUDIO_TASKS].create_index(
            [("status", 1), ("created_at", 1)],
            name="idx_audio_tasks_status_date"
        )
        await db[COLLECTION_AUDIO_TASKS].create_index(
            [("lease_until", 1)],
            name="idx_audio_tasks_lease"
        )
        await db[COLLECTION_AUDIO_TASKS].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_audio_tasks_expires_at"
        )

        # 11. ai_usage_limits: unique (user_id, date)
        await db[COLLECTION_AI_USAGE_LIMITS].create_index(
            [("user_id", 1), ("date", 1)],
            unique=True,
            name="uq_ai_usage_limits_user_date"
        )

        # 12. localization_rate_limits: TTL index
        await db[COLLECTION_LOCALIZATION_RATE_LIMITS].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_localization_rate_limits"
        )

        # 13. ui_translation_bundles: unique (namespace, locale, source_hash)
        await db[COLLECTION_UI_TRANSLATION_BUNDLES].create_index(
            [("namespace", 1), ("locale", 1), ("source_hash", 1)],
            unique=True,
            name="uq_ui_bundles_ns_loc_hash"
        )

        # 14. analytics_devices: unique token_hash & last_seen
        await db[COLLECTION_ANALYTICS_DEVICES].create_index(
            [("token_hash", 1)],
            unique=True,
            name="uq_analytics_devices_token_hash"
        )
        await db[COLLECTION_ANALYTICS_DEVICES].create_index(
            [("last_seen_at", -1)],
            name="idx_analytics_devices_last_seen"
        )

        # 15. analytics_sessions: visitor sessions
        await db[COLLECTION_ANALYTICS_SESSIONS].create_index(
            [("session_id", 1)],
            unique=True,
            name="uq_analytics_sessions_session_id"
        )
        await db[COLLECTION_ANALYTICS_SESSIONS].create_index(
            [("device_id", 1), ("status", 1), ("last_seen_at", -1)],
            name="idx_analytics_sessions_device_status_seen"
        )
        await db[COLLECTION_ANALYTICS_SESSIONS].create_index(
            [("started_at", -1)],
            name="idx_analytics_sessions_started_at"
        )

        # 15b. tour_sessions: unique tour_session_id, idempotency and progress
        await db[COLLECTION_TOUR_SESSIONS].create_index(
            [("tour_session_id", 1)],
            unique=True,
            name="uq_tour_sessions_id"
        )
        await db[COLLECTION_TOUR_SESSIONS].create_index(
            [("idempotency_key", 1)],
            unique=True,
            sparse=True,
            name="uq_tour_sessions_idempotency"
        )
        await db[COLLECTION_TOUR_SESSIONS].create_index(
            [("visitor_session_id", 1), ("started_at", -1)],
            name="idx_tour_sessions_visitor_started"
        )
        await db[COLLECTION_TOUR_SESSIONS].create_index(
            [("device_id", 1), ("status", 1), ("last_activity_at", -1)],
            name="idx_tour_sessions_device_status_act"
        )
        await db[COLLECTION_TOUR_SESSIONS].create_index(
            [("tour_id", 1), ("started_at", -1)],
            name="idx_tour_sessions_tour_started"
        )

        # 16. analytics_events: session_id, poi_id, occurred_at, playback_id
        await db[COLLECTION_ANALYTICS_EVENTS].create_index(
            [("session_id", 1), ("occurred_at", 1)],
            name="idx_analytics_events_session_date"
        )
        await db[COLLECTION_ANALYTICS_EVENTS].create_index(
            [("playback_id", 1), ("event_type", 1)],
            name="idx_analytics_events_playback_type"
        )
        await db[COLLECTION_ANALYTICS_EVENTS].create_index(
            [("server_received_at", -1), ("event_type", 1)],
            name="idx_analytics_events_recv_type"
        )
        await db[COLLECTION_ANALYTICS_EVENTS].create_index(
            [("poi_id", 1), ("event_type", 1), ("server_received_at", -1)],
            name="idx_analytics_events_poi_type_date"
        )
        await db[COLLECTION_ANALYTICS_EVENTS].create_index(
            [("tour_id", 1), ("event_type", 1), ("server_received_at", -1)],
            name="idx_analytics_events_tour_type_date"
        )

        # 17. analytics_poi_daily_metrics: unique (poi_id, metric_date, env)
        await db[COLLECTION_ANALYTICS_POI_DAILY_METRICS].create_index(
            [("poi_id", 1), ("metric_date", 1), ("env", 1)],
            unique=True,
            name="uq_analytics_poi_daily"
        )

        # 18. analytics_daily_metrics: unique (metric_date, env)
        await db[COLLECTION_ANALYTICS_DAILY_METRICS].create_index(
            [("metric_date", 1), ("env", 1)],
            unique=True,
            name="uq_analytics_daily"
        )

        # 19. analytics_hourly_metrics: unique (metric_date, metric_hour, env)
        await db[COLLECTION_ANALYTICS_HOURLY_METRICS].create_index(
            [("metric_date", 1), ("metric_hour", 1), ("env", 1)],
            unique=True,
            name="uq_analytics_hourly"
        )

        # 20. analytics_aggregation_jobs: unique (metric_date, env)
        await db[COLLECTION_ANALYTICS_AGGREGATION_JOBS].create_index(
            [("metric_date", 1), ("env", 1)],
            unique=True,
            name="uq_analytics_aggregation_jobs"
        )

        # 21. runtime_location_hourly: unique (time_hour, cell_id) + TTL
        await db[COLLECTION_RUNTIME_LOCATION_HOURLY].create_index(
            [("time_hour", 1), ("cell_id", 1)],
            unique=True,
            name="uq_runtime_location_hourly"
        )
        await db[COLLECTION_RUNTIME_LOCATION_HOURLY].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_runtime_location_hourly"
        )

        # 22. tours: active tour queries
        await db[COLLECTION_TOURS].create_index(
            [("is_active", 1), ("deleted_at", 1)],
            name="idx_tours_active"
        )

        # 23. qr_codes: unique code lookup
        await db[COLLECTION_QR_CODES].create_index(
            [("code", 1)],
            unique=True,
            name="uq_qr_codes_code"
        )
        await db[COLLECTION_QR_CODES].create_index(
            [("poi_id", 1), ("is_active", 1)],
            name="idx_qr_codes_poi_active"
        )

        # 24. auth_sessions: user query + TTL index on expires_at + token hash
        await db[COLLECTION_AUTH_SESSIONS].create_index(
            [("user_id", 1), ("revoked_at", 1)],
            name="idx_auth_sessions_user_revoked"
        )
        await db[COLLECTION_AUTH_SESSIONS].create_index(
            [("token_family_id", 1)],
            name="idx_auth_sessions_family"
        )
        await db[COLLECTION_AUTH_SESSIONS].create_index(
            [("refresh_token_hash", 1)],
            name="idx_auth_sessions_token_hash"
        )
        await db[COLLECTION_AUTH_SESSIONS].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_auth_sessions_expires_at"
        )

        # 25. idempotency_keys: unique (scope, actor_id, key) + TTL 24h
        await db[COLLECTION_IDEMPOTENCY_KEYS].create_index(
            [("scope", 1), ("actor_id", 1), ("key", 1)],
            unique=True,
            name="uq_idempotency_scope_actor_key"
        )
        await db[COLLECTION_IDEMPOTENCY_KEYS].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_idempotency_expires_at"
        )

        # 26. offline_pack_manifests: scope, locale, version lookup
        await db[COLLECTION_OFFLINE_PACK_MANIFESTS].create_index(
            [("scope", 1), ("locale", 1), ("version", 1)],
            unique=True,
            name="uq_offline_pack_scope_loc_ver"
        )

        # 27. auth_identities: Google/OIDC identities linked to user_id
        await db[COLLECTION_AUTH_IDENTITIES].create_index(
            [("provider", 1), ("issuer", 1), ("subject", 1)],
            unique=True,
            name="uq_auth_identities_sub"
        )
        await db[COLLECTION_AUTH_IDENTITIES].create_index(
            [("user_id", 1), ("provider", 1)],
            unique=True,
            name="uq_auth_identities_user_provider"
        )
        await db[COLLECTION_AUTH_IDENTITIES].create_index(
            [("user_id", 1)],
            name="idx_auth_identities_user_id"
        )

        # 28. auth_action_tokens: one-time action tokens (password reset)
        await db[COLLECTION_AUTH_ACTION_TOKENS].create_index(
            [("token_hash", 1)],
            unique=True,
            name="uq_action_token_hash"
        )
        await db[COLLECTION_AUTH_ACTION_TOKENS].create_index(
            [("user_id", 1), ("purpose", 1), ("consumed_at", 1)],
            name="idx_action_tokens_user_purpose"
        )
        await db[COLLECTION_AUTH_ACTION_TOKENS].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_action_tokens_expires_at"
        )

        # 29. oauth_transactions: transient state & PKCE verifier
        await db[COLLECTION_OAUTH_TRANSACTIONS].create_index(
            [("state", 1)],
            unique=True,
            name="uq_oauth_transactions_state"
        )
        await db[COLLECTION_OAUTH_TRANSACTIONS].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_oauth_transactions_expires_at"
        )

        # 30. guest_sessions: unique credential hash, claimed user, TTL expiry
        await db[COLLECTION_GUEST_SESSIONS].create_index(
            [("credential_hash", 1)],
            unique=True,
            name="uq_guest_credential_hash"
        )
        await db[COLLECTION_GUEST_SESSIONS].create_index(
            [("claimed_user_id", 1)],
            name="idx_guest_claimed_user"
        )
        await db[COLLECTION_GUEST_SESSIONS].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_guest_sessions_expires_at"
        )

        # 31. trial_usage: unique compound (subject_type, subject_id, policy_version)
        await db[COLLECTION_TRIAL_USAGE].create_index(
            [("subject_type", 1), ("subject_id", 1), ("policy_version", 1)],
            unique=True,
            name="uq_trial_subject_policy"
        )
        await db[COLLECTION_TRIAL_USAGE].create_index(
            [("state", 1), ("reservation_expires_at", 1)],
            name="idx_trial_reservation"
        )

        # 32. playback_grants: unique grant token, subject lookup, TTL expiry
        await db[COLLECTION_PLAYBACK_GRANTS].create_index(
            [("grant_token", 1)],
            unique=True,
            name="uq_playback_grant_token"
        )
        await db[COLLECTION_PLAYBACK_GRANTS].create_index(
            [("subject_id", 1), ("poi_id", 1)],
            name="idx_playback_subject_poi"
        )
        await db[COLLECTION_PLAYBACK_GRANTS].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_playback_grants_expires_at"
        )

        # 33. orders: unique user+idempotency, user orders, status+expires
        await db[COLLECTION_ORDERS].create_index(
            [("user_id", 1), ("idempotency_key", 1)],
            unique=True,
            sparse=True,
            name="uq_orders_user_idempotency"
        )
        await db[COLLECTION_ORDERS].create_index(
            [("user_id", 1), ("created_at", -1)],
            name="idx_orders_user_created"
        )
        await db[COLLECTION_ORDERS].create_index(
            [("status", 1), ("expires_at", 1)],
            name="idx_orders_status_expires"
        )

        # 34. payment_attempts: unique provider reference, order lookup, tx id
        await db[COLLECTION_PAYMENT_ATTEMPTS].create_index(
            [("provider", 1), ("provider_reference", 1)],
            unique=True,
            name="uq_payment_provider_ref"
        )
        await db[COLLECTION_PAYMENT_ATTEMPTS].create_index(
            [("order_id", 1), ("created_at", -1)],
            name="idx_payment_attempts_order"
        )
        await db[COLLECTION_PAYMENT_ATTEMPTS].create_index(
            [("provider", 1), ("provider_transaction_id", 1)],
            sparse=True,
            name="idx_payment_provider_tx"
        )

        # 35. payment_events: idempotent webhook events ledger
        await db[COLLECTION_PAYMENT_EVENTS].create_index(
            [("provider", 1), ("event_key", 1)],
            unique=True,
            name="uq_payment_events_key"
        )
        await db[COLLECTION_PAYMENT_EVENTS].create_index(
            [("processing_state", 1), ("received_at", -1)],
            name="idx_payment_events_state"
        )

        # 36. tour_entitlements: unique user+tour ownership, user lookup
        await db[COLLECTION_TOUR_ENTITLEMENTS].create_index(
            [("user_id", 1), ("tour_id", 1)],
            unique=True,
            name="uq_user_tour_entitlement"
        )
        await db[COLLECTION_TOUR_ENTITLEMENTS].create_index(
            [("user_id", 1), ("status", 1)],
            name="idx_entitlements_user_status"
        )

        # 37. route_cache: unique fingerprint, TTL auto-expiration, mode lookup
        await db[COLLECTION_ROUTE_CACHE].create_index(
            [("fingerprint", 1)],
            unique=True,
            name="uq_route_cache_fingerprint"
        )
        await db[COLLECTION_ROUTE_CACHE].create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="ttl_route_cache_expires_at"
        )
        await db[COLLECTION_ROUTE_CACHE].create_index(
            [("mode", 1), ("created_at", -1)],
            name="idx_route_cache_mode_date"
        )

        logger.info("All collection indexes created successfully!")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise e

