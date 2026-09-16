"""Service for Admin Moderation operations:
- C06 / C07 / SD10 / AD10
- Reviews owner registrations and POI submissions with optimistic concurrency checks.
"""

from typing import Any, Dict, List, Optional
import uuid

from app.repositories.owner_repo import owner_repo
from app.repositories.poi_repo import poi_repo
from app.services.poi_admin_service import poi_admin_service


class ModerationService:
    async def list_pending_registrations(self) -> List[Dict[str, Any]]:
        return await owner_repo.list_pending_registrations()

    async def review_registration(
        self,
        registration_id: str,
        decision: str,  # 'approved' or 'rejected'
        admin_id: str,
        admin_note: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """Reviews owner registration."""
        if decision not in ("approved", "rejected"):
            return {"success": False, "error": "Quyết định không hợp lệ."}

        reg = await owner_repo.get_by_id(registration_id)
        if not reg:
            return {"success": False, "error": "Hồ sơ đăng ký không tồn tại."}

        if reg.get("status") != "pending":
            return {"success": False, "error": f"Hồ sơ đã được xử lý trước đó ({reg.get('status')})."}

        updated = await owner_repo.review_registration(
            registration_id=registration_id,
            status=decision,
            admin_id=admin_id,
            admin_note=admin_note,
            expected_version=expected_version
        )

        if not updated:
            return {"success": False, "error": "Xung đột phiên bản kiểm duyệt (Version conflict)."}

        # Send in-app notification to the owner
        msg = f"Đơn đăng ký chủ quán của bạn đã được {'chấp thuận' if decision == 'approved' else 'từ chối'}."
        if admin_note:
            msg += f" Ghi chú: {admin_note}"

        await owner_repo.create_notification(
            owner_id=reg["user_id"],
            type="registration_result",
            message=msg,
            registration_id=registration_id
        )

        return {
            "success": True,
            "registration_id": registration_id,
            "status": decision,
            "message": f"Đã { 'chấp thuận' if decision == 'approved' else 'từ chối' } đơn đăng ký chủ quán."
        }

    async def list_pending_submissions(self) -> List[Dict[str, Any]]:
        return await owner_repo.list_submissions(status="pending")

    async def review_submission(
        self,
        submission_id: str,
        decision: str,  # 'approved' or 'rejected'
        admin_id: str,
        admin_note: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """Reviews POI content submission."""
        if decision not in ("approved", "rejected"):
            return {"success": False, "error": "Quyết định không hợp lệ."}

        sub = await owner_repo.get_submission(submission_id)
        if not sub:
            return {"success": False, "error": "Đề xuất nội dung không tồn tại."}

        if sub.get("status") != "pending":
            return {"success": False, "error": f"Đề xuất đã được xử lý trước đó ({sub.get('status')})."}

        updated = await owner_repo.review_submission(
            submission_id=submission_id,
            status=decision,
            admin_id=admin_id,
            admin_note=admin_note,
            expected_version=expected_version
        )

        if not updated:
            return {"success": False, "error": "Xung đột phiên bản kiểm duyệt (Version conflict)."}

        # If approved, apply payload to POI
        applied_poi_id = sub.get("poi_id")
        if decision == "approved":
            payload = sub.get("payload", {})
            action = sub.get("action", "create")

            if action == "create":
                payload["owner_id"] = sub["owner_id"]
                created_poi = await poi_admin_service.create_poi(payload, created_by=admin_id)
                applied_poi_id = created_poi["_id"]
            elif action == "update" and applied_poi_id:
                # Update existing POI
                poi = await poi_repo.get_by_id(applied_poi_id)
                if poi:
                    await poi_admin_service.update_poi(
                        poi_id=applied_poi_id,
                        update_fields=payload,
                        expected_version=poi.get("version", 1),
                        content_changed=True
                    )

        # Send in-app notification to owner
        msg = f"Đề xuất nội dung của bạn đã được {'phê duyệt' if decision == 'approved' else 'từ chối'}."
        if admin_note:
            msg += f" Ghi chú: {admin_note}"

        await owner_repo.create_notification(
            owner_id=sub["owner_id"],
            type="submission_result",
            message=msg,
            submission_id=submission_id
        )

        return {
            "success": True,
            "submission_id": submission_id,
            "status": decision,
            "applied_poi_id": applied_poi_id,
            "message": f"Đã { 'phê duyệt' if decision == 'approved' else 'từ chối' } đề xuất nội dung."
        }


moderation_service = ModerationService()
