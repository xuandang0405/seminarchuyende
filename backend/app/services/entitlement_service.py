"""Service for Tour Entitlements Management.

Section 7, 8 & 9 of prompt.
BR-PAY-06..08.
"""

from typing import Any, Dict, List, Optional
from app.repositories.entitlement_repo import entitlement_repo
from app.repositories.tour_repo import tour_repo


class EntitlementService:
    async def has_tour_entitlement(self, user_id: Optional[str], tour_id: str) -> bool:
        """Checks if a user owns an active entitlement for the specified tour."""
        if not user_id or not tour_id:
            return False
        entitlement = await entitlement_repo.get_entitlement(user_id, tour_id)
        return bool(entitlement and entitlement.get("status") == "active")

    async def grant_entitlement(
        self,
        user_id: str,
        tour_id: str,
        source_order_id: str,
        session=None
    ) -> Dict[str, Any]:
        """Issues an active tour entitlement."""
        return await entitlement_repo.create_entitlement(
            user_id=user_id,
            tour_id=tour_id,
            source_order_id=source_order_id,
            session=session
        )

    async def get_user_entitled_tours(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns full tour details for all tours purchased by the user."""
        entitlements = await entitlement_repo.list_user_entitlements(user_id)
        results = []
        for ent in entitlements:
            tour = await tour_repo.get_by_id(ent["tour_id"])
            if tour:
                results.append({
                    "_id": tour["_id"],
                    "tour_id": tour["_id"],
                    "tour_title": tour.get("name"),
                    "code": tour.get("code"),
                    "poi_ids": tour.get("poi_ids", []),
                    "entitlement_id": ent["_id"],
                    "source_order_id": ent["source_order_id"],
                    "granted_at": ent["granted_at"],
                    "can_download_offline": True,
                    "preview_enabled": tour.get("preview_enabled", True)
                })
        return results


entitlement_service = EntitlementService()
