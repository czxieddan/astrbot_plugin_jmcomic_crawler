from __future__ import annotations

from typing import Any


class PermissionService:
    def __init__(self, config: dict):
        self.config = config or {}

    def get_sender_id(self, event: Any) -> str:
        getter = getattr(event, "get_sender_id", None)
        if callable(getter):
            try:
                return str(getter())
            except Exception:
                pass

        getter = getattr(event, "get_sender_name", None)
        if callable(getter):
            try:
                return str(getter())
            except Exception:
                pass

        sender = getattr(event, "sender", None)
        if sender is not None:
            return str(sender)

        return "unknown"

    def is_admin(self, event: Any) -> bool:
        if not bool(self.config.get("admin_only_download", True)):
            return True
        sender_id = self.get_sender_id(event)
        return sender_id in self._admin_users()

    def _admin_users(self) -> list[str]:
        value = self.config.get("admin_users")
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []