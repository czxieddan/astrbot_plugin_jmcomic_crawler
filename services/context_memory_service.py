from __future__ import annotations

from typing import Any


class ContextMemoryService:
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager

    def get_session_id(self, event: Any | None) -> str:
        if event is None:
            return "global"

        for attr in ("session_id", "conversation_id", "unified_msg_origin"):
            value = getattr(event, attr, None)
            if value:
                return str(value)

        getter = getattr(event, "get_sender_id", None)
        if callable(getter):
            try:
                return f"user:{getter()}"
            except Exception:
                pass

        sender = getattr(event, "sender", None)
        if sender is not None:
            return f"user:{sender}"

        return "global"

    def remember_album(self, event: Any | None, album_id: str) -> dict:
        return self.memory_manager.set_last_album(self.get_session_id(event), album_id)

    def remember_chapter(self, event: Any | None, chapter_id: str) -> dict:
        return self.memory_manager.set_last_chapter(self.get_session_id(event), chapter_id)

    def remember_task(self, event: Any | None, task_id: str) -> dict:
        return self.memory_manager.set_last_task(self.get_session_id(event), task_id)

    def get_memory(self, event: Any | None) -> dict:
        return self.memory_manager.get(self.get_session_id(event))

    def resolve_album(self, event: Any | None, album_id: str | None = None) -> str | None:
        if album_id:
            return album_id
        return self.get_memory(event).get("last_album_id")

    def resolve_chapter(self, event: Any | None, chapter_id: str | None = None) -> str | None:
        if chapter_id:
            return chapter_id
        return self.get_memory(event).get("last_chapter_id")

    def resolve_task(self, event: Any | None, task_id: str | None = None) -> str | None:
        if task_id:
            return task_id
        return self.get_memory(event).get("last_task_id")