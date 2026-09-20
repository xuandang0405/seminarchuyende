"""Service for MenuItem operations.

T06 / C05 / O09.
Enforces ownership validation for owners managing their own POI menus.
"""

from typing import Any, Dict, List, Optional
import uuid

from app.repositories.menu_repo import menu_repo
from app.repositories.poi_repo import poi_repo


class MenuService:
    async def get_poi_menu(self, poi_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        return await menu_repo.find_by_poi(poi_id, include_inactive=include_inactive)

    async def create_menu_item(
        self,
        poi_id: str,
        payload: Dict[str, Any],
        actor_id: str,
        actor_role: str
    ) -> Dict[str, Any]:
        # Enforce RBAC: only admins or POI owners can manage menu items
        if actor_role not in ("super_admin", "admin", "poi_owner"):
            return {"success": False, "error": "Bạn không có quyền thêm món vào thực đơn."}

        poi = await poi_repo.get_by_id(poi_id)
        if not poi:
            return {"success": False, "error": "Địa điểm không tồn tại."}

        # Check ownership if caller is poi_owner
        if actor_role == "poi_owner" and poi.get("owner_id") != actor_id:
            return {"success": False, "error": "Bạn không có quyền quản lý menu của địa điểm này."}

        price = int(payload.get("price", 0))
        if price < 0:
            return {"success": False, "error": "Giá món ăn không được âm."}

        doc = {
            "_id": f"menu_{uuid.uuid4().hex[:12]}",
            "poi_id": poi_id,
            "name": payload["name"],
            "description": payload.get("description", ""),
            "price": price,
            "currency": payload.get("currency", "VND"),
            "image_url": payload.get("image_url"),
            "is_active": payload.get("is_active", True),
        }
        created = await menu_repo.create_menu_item(doc)
        return {"success": True, "item": created}

    async def update_menu_item(
        self,
        item_id: str,
        payload: Dict[str, Any],
        actor_id: str,
        actor_role: str,
        expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        # Enforce RBAC: only admins or POI owners can manage menu items
        if actor_role not in ("super_admin", "admin", "poi_owner"):
            return {"success": False, "error": "Bạn không có quyền chỉnh sửa món ăn này."}

        item = await menu_repo.get_by_id_active(item_id)
        if not item:
            return {"success": False, "error": "Món ăn không tồn tại."}

        # Check POI ownership
        if actor_role == "poi_owner":
            poi = await poi_repo.get_by_id(item["poi_id"])
            if not poi or poi.get("owner_id") != actor_id:
                return {"success": False, "error": "Bạn không có quyền chỉnh sửa món ăn này."}

        update_fields = {}
        if "name" in payload:
            update_fields["name"] = payload["name"]
        if "description" in payload:
            update_fields["description"] = payload["description"]
        if "price" in payload:
            price = int(payload["price"])
            if price < 0:
                return {"success": False, "error": "Giá món ăn không được âm."}
            update_fields["price"] = price
        if "image_url" in payload:
            update_fields["image_url"] = payload["image_url"]
        if "is_active" in payload:
            update_fields["is_active"] = payload["is_active"]

        updated = await menu_repo.update_menu_item(item_id, update_fields, expected_version)
        if not updated:
            return {"success": False, "error": "Xung đột phiên bản món ăn (Version conflict)."}

        return {"success": True, "item": updated}

    async def delete_menu_item(self, item_id: str, actor_id: str, actor_role: str) -> Dict[str, Any]:
        # Enforce RBAC: only admins or POI owners can manage menu items
        if actor_role not in ("super_admin", "admin", "poi_owner"):
            return {"success": False, "error": "Bạn không có quyền xóa món ăn này."}

        item = await menu_repo.get_by_id_active(item_id)
        if not item:
            return {"success": False, "error": "Món ăn không tồn tại."}

        if actor_role == "poi_owner":
            # Master Prompt Section 10: "Owner không mặc định có menu:delete; nếu cần ẩn món, dùng cập nhật trạng thái trong phạm vi được phép"
            poi = await poi_repo.get_by_id(item["poi_id"])
            if not poi or poi.get("owner_id") != actor_id:
                return {"success": False, "error": "Bạn không có quyền quản lý món ăn này."}
            # Deactivate instead of deleting
            await menu_repo.update_menu_item(item_id, {"is_active": False})
            return {"success": True, "message": "Món ăn đã được chuyển sang trạng thái ẩn."}

        # Admin delete
        deleted = await menu_repo.soft_delete(item_id)
        return {"success": deleted, "message": "Món ăn đã được xóa."}


menu_service = MenuService()
