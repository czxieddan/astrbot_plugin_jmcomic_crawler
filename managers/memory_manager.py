from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional


class MemoryManager:
    def __init__(self, base_dir: str, enabled: bool = True, ttl_seconds: int = 3600):
        self.enabled = enabled
        self.ttl_seconds = max(60, int(ttl_seconds or 3600))
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get(self, session_id: str) -> dict[str, Any]:
        if not self.enabled:
            return {}

        path = self._path(session_id)
        if not path.exists():
            return {}

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

        if time.time() > payload.get("expires_at", 0):
            self.clear(session_id)
            return {}

        return payload.get("value") or {}

    def update(self, session_id: str, values: dict[str, Any]) -> dict[str, Any]:
        current = self.get(session_id)
        current.update({k: v for k, v in values.items() if v not in (None, "", [], {})})
        self._save(session_id, current)
        return current

    def set_last_album(self, session_id: str, album_id: str) -> dict[str, Any]:
        return self.update(session_id, {"last_album_id": album_id})

    def set_last_chapter(self, session_id: str, chapter_id: str) -> dict[str, Any]:
        return self.update(session_id, {"last_chapter_id": chapter_id})

    def set_last_task(self, session_id: str, task_id: str) -> dict[str, Any]:
        return self.update(session_id, {"last_task_id": task_id})

    def clear(self, session_id: str) -> None:
        path = self._path(session_id)
        if path.exists():
            path.unlink()

    def _save(self, session_id: str, value: dict[str, Any]) -> None:
        if not self.enabled:
            return

        payload = {
            "expires_at": time.time() + self.ttl_seconds,
            "value": value,
        }
        path = self._path(session_id)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.json"