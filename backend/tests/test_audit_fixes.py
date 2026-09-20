import pytest
import time
from httpx import AsyncClient
from app.core.security import create_access_token
from app.db.collections import COLLECTION_ADMIN_USERS, COLLECTION_MENU_ITEM, COLLECTION_POI
from app.core.database import db_manager


@pytest.mark.asyncio
async def test_sec_002_user_cannot_delete_or_create_menu_item(client: AsyncClient):
    """Verifies that a normal user (tourist) cannot create or delete menu items (SEC-002)."""
    db = db_manager.db
    user_id = f"test_user_tourist_{int(time.time()*1000)}"
    await db[COLLECTION_ADMIN_USERS].insert_one({
        "_id": user_id,
        "email": f"{user_id}@test.vn",
        "role": "user",
        "is_active": True,
        "auth_version": 1
    })
    token = create_access_token(user_id, claims={"role": "user", "auth_version": 1})

    # 1. Attempt to create menu item as normal user -> 403 Forbidden
    res_create = await client.post(
        "/api/v1/pois/poi_ben_nha_rong/menu",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Món lậu độc hại", "price": 50000}
    )
    assert res_create.status_code == 403, f"Expected 403 Forbidden, got {res_create.status_code}"

    # 2. Attempt to delete menu item as normal user -> 403 Forbidden
    res_del = await client.delete(
        "/api/v1/menu/menu_sample_01",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_del.status_code == 403, f"Expected 403 Forbidden, got {res_del.status_code}"


@pytest.mark.asyncio
async def test_mongo_001_search_redos_safe(client: AsyncClient):
    """Verifies that malicious regex characters in search do not trigger ReDoS or crashes (MONGO-001)."""
    evil_payload = "((a+)+)+$"
    start = time.time()
    res = await client.get(f"/api/v1/pois?search={evil_payload}")
    duration = time.time() - start
    assert res.status_code == 200
    assert duration < 1.0, f"ReDoS query took too long: {duration}s"


@pytest.mark.asyncio
async def test_sec_001_cors_restriction(client: AsyncClient):
    """Verifies that untrusted origins are not automatically granted credentials (SEC-001)."""
    headers = {
        "Origin": "https://malicious-site.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type"
    }
    res = await client.options("/api/v1/auth/login", headers=headers)
    allow_origin = res.headers.get("access-control-allow-origin")
    allow_cred = res.headers.get("access-control-allow-credentials")
    if allow_cred == "true":
        assert allow_origin != "https://malicious-site.com"


@pytest.mark.asyncio
async def test_poi_nearby_bounds_validation(client: AsyncClient):
    """Verifies boundary checks on nearby query (FAST-003)."""
    # Latitude out of bounds (> 90) -> 422 Unprocessable Entity
    res = await client.get("/api/v1/pois/nearby?longitude=106.7&latitude=999&max_distance_meters=1000")
    assert res.status_code == 422
