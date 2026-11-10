"""Real MongoDB replica-set acceptance check. Uses and removes only its unique test database."""
import asyncio
import os
import uuid
os.environ.update(APP_ENV="test", PAYMENT_MODE="mock", ALLOW_MOCK_DATABASE="false",
                  SECRET_KEY="ci-process-only-secret-" + uuid.uuid4().hex)
from pymongo import AsyncMongoClient
from fastapi import HTTPException
from app.core.database import db_manager
from app.core.config import settings
from app.db.indexes import create_all_indexes
from app.db.collections import (COLLECTION_TOURS, COLLECTION_TOUR_ENTITLEMENTS, COLLECTION_ORDERS,
    COLLECTION_POI, COLLECTION_POI_SUBMISSIONS, COLLECTION_AUDIO_TASKS, COLLECTION_POI_OWNER_REGISTRATIONS,
    COLLECTION_ADMIN_USERS)
from app.services.order_service import order_service
from app.services.payment_service import payment_service
from app.repositories.order_repo import order_repo

async def main():
    uri = os.environ.get("MONGO_TEST_URI", "mongodb://127.0.0.1:27028/?directConnection=true&replicaSet=rs0")
    client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True)
    name = "tourvoice_ci_" + uuid.uuid4().hex
    db = client[name]
    db_manager.client, db_manager.db, db_manager.is_mock, db_manager.is_connected = client, db, False, True
    try:
        assert (await client.admin.command("hello")).get("setName"), "Replica set required"
        await create_all_indexes(db)
        await create_all_indexes(db)
        await db[COLLECTION_TOURS].insert_one({"_id": "ci-tour", "name": "CI tour", "price_amount": 99000,
                                              "pricing_version": 1, "is_active": True, "is_purchasable": True})
        orders = await asyncio.gather(*(order_service.create_tour_order("ci-user", "ci-tour", "ci-idempotent") for _ in range(5)))
        assert len({o["_id"] for o in orders}) == 1, "Concurrent checkout created duplicate orders"
        order = orders[0]
        other_clicks = await asyncio.gather(*(order_service.create_tour_order("ci-user", "ci-tour", f"ci-tab-{i}") for i in range(3)))
        assert all(item["_id"] == order["_id"] for item in other_clicks), "Different tabs created payable duplicate orders"
        attempts = await asyncio.gather(*(payment_service.create_payment_attempt(order["_id"], "vietqr", "ci-user")
                                         for _ in range(5)), return_exceptions=True)
        assert all(isinstance(item, dict) or isinstance(item, HTTPException) and item.status_code == 409 for item in attempts)
        attempt = next(item for item in attempts if isinstance(item, dict))
        assert await order_repo.attempt_collection.count_documents({"order_id": order["_id"]}) == 1
        payload = {"provider_reference": attempt["provider_reference"], "amount": 99000, "transaction_id": "ci-transaction"}
        responses = await asyncio.gather(*(payment_service.handle_provider_webhook("mock", payload) for _ in range(5)))
        assert all(r["status"] == "ok" for r in responses)
        assert await db[COLLECTION_TOUR_ENTITLEMENTS].count_documents({"user_id": "ci-user", "tour_id": "ci-tour"}) == 1
        settled = await db[COLLECTION_ORDERS].find_one({"_id": order["_id"]})
        assert settled["status"] == "paid" and settled.get("ticket_code")
        await order_repo.update_order_status(order["_id"], "requires_review")
        late_attempt = await order_repo.update_attempt_state(attempt["attempt_id"], "failed")
        assert late_attempt["state"] == "succeeded"
        assert (await order_repo.get_by_id(order["_id"]))["status"] == "paid"
        # Prove a failed transaction cannot leave partial order/payment writes.
        async with client.start_session() as session:
            try:
                async with await session.start_transaction():
                    await db[COLLECTION_ORDERS].update_one({"_id": order["_id"]}, {"$set": {"status": "corrupt"}}, session=session)
                    raise RuntimeError("injected failure")
            except RuntimeError:
                pass
        assert (await db[COLLECTION_ORDERS].find_one({"_id": order["_id"]}))["status"] == "paid"
        from app.repositories.owner_repo import owner_repo
        from app.services.moderation_service import moderation_service
        await db[COLLECTION_ADMIN_USERS].insert_one({"_id": "ci-owner", "is_poi_owner_verified": False})
        reg = await owner_repo.create_registration("ci-owner", "CI business")
        sub = await owner_repo.create_submission("ci-owner", "create", {
            "name": "CI POI", "description": "Transaction test content only",
            "location": {"type": "Point", "coordinates": [106.7, 10.76]}})
        original_notification = owner_repo.create_notification
        async def fail_notification(*args, **kwargs):
            raise RuntimeError("injected notification write failure")
        owner_repo.create_notification = fail_notification
        try:
            for operation in (
                lambda: moderation_service.review_registration(reg["_id"], "approved", "ci-admin"),
                lambda: moderation_service.review_submission(sub["_id"], "approved", "ci-admin"),
            ):
                try:
                    await operation()
                    raise AssertionError("Expected failed transaction")
                except HTTPException as exc:
                    assert exc.status_code == 503
        finally:
            owner_repo.create_notification = original_notification
        assert (await db[COLLECTION_POI_OWNER_REGISTRATIONS].find_one({"_id": reg["_id"]}))["status"] == "pending"
        assert not (await db[COLLECTION_ADMIN_USERS].find_one({"_id": "ci-owner"}))["is_poi_owner_verified"]
        assert (await db[COLLECTION_POI_SUBMISSIONS].find_one({"_id": sub["_id"]}))["status"] == "pending"
        assert await db[COLLECTION_POI].count_documents({}) == 0
        assert await db[COLLECTION_AUDIO_TASKS].count_documents({}) == 0
        assert (await moderation_service.review_registration(reg["_id"], "approved", "ci-admin"))["success"]
        reviews = await asyncio.gather(*(moderation_service.review_submission(sub["_id"], "approved", "ci-admin") for _ in range(3)))
        assert sum(bool(r.get("success")) for r in reviews) == 1
        assert await db[COLLECTION_POI].count_documents({}) == 1
        assert await db[COLLECTION_AUDIO_TASKS].count_documents({}) == 1
        print("PASS: replica-set indexes, concurrent idempotent checkout, settlement/callbacks, moderation rollback and concurrent review")
    finally:
        assert name.startswith("tourvoice_ci_")
        await client.drop_database(name)
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
