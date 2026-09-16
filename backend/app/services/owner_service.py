"""Service for POI Owner portal operations:
- O02 / O03 / O04 / O05 / O06 / O07 / O08 / SD09 / AD09
- IDOR Protection: Owner can only access POIs, submissions, and notifications belonging to themselves.
"""

from typing import Any, Dict, List, Optional
from app.repositories.owner_repo import owner_repo
from app.repositories.poi_repo import poi_repo
from app.repositories.auth_repo import auth_repo


class OwnerService:
    async def get_registration_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await owner_repo.get_registration_by_user(user_id)

    async def get_my_pois(self, owner_id: str, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns POIs belonging strictly to this owner."""
        return await poi_repo.find_by_owner(owner_id=owner_id, skip=skip, limit=limit)

    async def submit_content(
        self,
        owner_id: str,
        action: str,  # 'create' or 'update'
        payload: Dict[str, Any],
        poi_id: Optional[str] = None,
        request_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submits a POI draft for Admin moderation."""
        # 1. Verify owner account
        user = await auth_repo.get_user_by_id(owner_id)
        if not user or not user.get("is_poi_owner_verified", False):
            return {
                "success": False,
                "error": "Tài khoản chủ quán chưa được Admin xác minh. Vui lòng chờ duyệt đăng ký."
            }

        # 2. If update, check ownership
        if action == "update":
            if not poi_id:
                return {"success": False, "error": "Thiếu poi_id cho thao tác cập nhật."}
            existing_poi = await poi_repo.get_by_id(poi_id)
            if not existing_poi or existing_poi.get("owner_id") != owner_id:
                return {"success": False, "error": "Bạn không có quyền chỉnh sửa địa điểm này."}

        # 3. Create pending submission
        submission = await owner_repo.create_submission(
            owner_id=owner_id,
            action=action,
            payload=payload,
            poi_id=poi_id,
            request_key=request_key
        )

        return {
            "success": True,
            "submission_id": submission["_id"],
            "status": "pending",
            "message": "Nội dung đã được gửi duyệt tới Ban quản trị."
        }

    async def list_my_submissions(self, owner_id: str) -> List[Dict[str, Any]]:
        return await owner_repo.list_submissions(owner_id=owner_id)

    async def list_my_notifications(self, owner_id: str) -> List[Dict[str, Any]]:
        return await owner_repo.list_notifications(owner_id=owner_id)

    async def mark_notification_read(self, notif_id: str, owner_id: str) -> bool:
        return await owner_repo.mark_notification_read(notif_id, owner_id)


owner_service = OwnerService()
