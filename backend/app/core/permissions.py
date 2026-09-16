"""Core permissions catalog and role mapping.

Tuân thủ catalog 32 permissions nền tảng từ Section 10 của Master Prompt:
- super_admin: priority 0 (toàn bộ 32 permissions)
- admin: priority 1
- poi_owner: priority 10
- user: priority 100
"""

# ==============================================================================
# CATALOG 32 PERMISSIONS
# ==============================================================================

# POI
PERM_POI_READ = "poi:read"
PERM_POI_CREATE = "poi:create"
PERM_POI_UPDATE = "poi:update"
PERM_POI_DELETE = "poi:delete"
PERM_POI_APPROVE = "poi:approve"
PERM_POI_TOGGLE = "poi:toggle"

# Menu
PERM_MENU_READ = "menu:read"
PERM_MENU_CREATE = "menu:create"
PERM_MENU_UPDATE = "menu:update"
PERM_MENU_DELETE = "menu:delete"

# User
PERM_USER_READ = "user:read"
PERM_USER_CREATE = "user:create"
PERM_USER_UPDATE = "user:update"
PERM_USER_DELETE = "user:delete"

# Role
PERM_ROLE_READ = "role:read"
PERM_ROLE_CREATE = "role:create"
PERM_ROLE_UPDATE = "role:update"
PERM_ROLE_DELETE = "role:delete"

# Analytics
PERM_ANALYTICS_VIEW = "analytics:view"
PERM_ANALYTICS_EXPORT = "analytics:export"
PERM_ANALYTICS_VIEW_OWN = "analytics:view_own"

# Audit
PERM_AUDIT_READ = "audit:read"
PERM_AUDIT_MANAGE = "audit:manage"

# System
PERM_SYSTEM_CONFIG = "system:config"
PERM_SYSTEM_LOGS = "system:logs"
PERM_SYSTEM_BACKUP = "system:backup"

# Owner
PERM_OWNER_REGISTER = "owner:register"
PERM_OWNER_ACCESS = "owner:access"
PERM_OWNER_SUBMIT_POI = "owner:submit_poi"
PERM_OWNER_MANAGE_OWN_POI = "owner:manage_own_poi"

# Content
PERM_CONTENT_MODERATE = "content:moderate"
PERM_CONTENT_PUBLISH = "content:publish"


ALL_PERMISSIONS = [
    # POI (6)
    PERM_POI_READ,
    PERM_POI_CREATE,
    PERM_POI_UPDATE,
    PERM_POI_DELETE,
    PERM_POI_APPROVE,
    PERM_POI_TOGGLE,
    # Menu (4)
    PERM_MENU_READ,
    PERM_MENU_CREATE,
    PERM_MENU_UPDATE,
    PERM_MENU_DELETE,
    # User (4)
    PERM_USER_READ,
    PERM_USER_CREATE,
    PERM_USER_UPDATE,
    PERM_USER_DELETE,
    # Role (4)
    PERM_ROLE_READ,
    PERM_ROLE_CREATE,
    PERM_ROLE_UPDATE,
    PERM_ROLE_DELETE,
    # Analytics (3)
    PERM_ANALYTICS_VIEW,
    PERM_ANALYTICS_EXPORT,
    PERM_ANALYTICS_VIEW_OWN,
    # Audit (2)
    PERM_AUDIT_READ,
    PERM_AUDIT_MANAGE,
    # System (3)
    PERM_SYSTEM_CONFIG,
    PERM_SYSTEM_LOGS,
    PERM_SYSTEM_BACKUP,
    # Owner (4)
    PERM_OWNER_REGISTER,
    PERM_OWNER_ACCESS,
    PERM_OWNER_SUBMIT_POI,
    PERM_OWNER_MANAGE_OWN_POI,
    # Content (2)
    PERM_CONTENT_MODERATE,
    PERM_CONTENT_PUBLISH,
]


# ==============================================================================
# DEFAULT ROLE PERMISSION MAPPINGS
# ==============================================================================

ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_POI_OWNER = "poi_owner"
ROLE_USER = "user"

ROLES_DEFINITION = {
    ROLE_SUPER_ADMIN: {
        "name": ROLE_SUPER_ADMIN,
        "priority": 0,
        "permissions": ALL_PERMISSIONS,
    },
    ROLE_ADMIN: {
        "name": ROLE_ADMIN,
        "priority": 1,
        "permissions": [
            PERM_POI_READ,
            PERM_POI_CREATE,
            PERM_POI_UPDATE,
            PERM_POI_DELETE,
            PERM_POI_APPROVE,
            PERM_POI_TOGGLE,
            PERM_MENU_READ,
            PERM_MENU_CREATE,
            PERM_MENU_UPDATE,
            PERM_MENU_DELETE,
            PERM_USER_READ,
            PERM_USER_CREATE,
            PERM_USER_UPDATE,
            PERM_ANALYTICS_VIEW,
            PERM_ANALYTICS_EXPORT,
            PERM_AUDIT_READ,
            PERM_CONTENT_MODERATE,
            PERM_CONTENT_PUBLISH,
            PERM_SYSTEM_LOGS,
        ],
    },
    ROLE_POI_OWNER: {
        "name": ROLE_POI_OWNER,
        "priority": 10,
        "permissions": [
            PERM_POI_READ,
            PERM_OWNER_ACCESS,
            PERM_OWNER_SUBMIT_POI,
            PERM_OWNER_MANAGE_OWN_POI,
            PERM_MENU_READ,
            PERM_MENU_CREATE,
            PERM_MENU_UPDATE,
            PERM_ANALYTICS_VIEW_OWN,
        ],
    },
    ROLE_USER: {
        "name": ROLE_USER,
        "priority": 100,
        "permissions": [
            PERM_POI_READ,
            PERM_MENU_READ,
            PERM_OWNER_REGISTER,
        ],
    },
}
