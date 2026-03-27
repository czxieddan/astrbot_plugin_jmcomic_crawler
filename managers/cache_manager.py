from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional


class CacheManager:
    def __init__(self, base_dir: str, enabled: bool = True):
        self.enabled = enabled
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get(self, namespace: str, key: str, ttl_seconds: int | None = None) -> Optional[Any]:
        if not self.enabled:
            return None

        path = self._path(namespace, key)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

        expires_at = payload.get("expires_at")
        if ttl_seconds is not None and expires_at is None:
            expires_at = payload.get("created_at", 0) + ttl_seconds

        if expires_at is not None and time.time() > expires_at:
            self.delete(namespace, key)
            return None

        return payload.get("value")

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        if not self.enabled:
            return

        now = time.time()
        payload = {
            "created_at": now,
            "expires_at": now + ttl_seconds if ttl_seconds else None,
            "value": value,
        }
        path = self._path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def delete(self, namespace: str, key: str) -> None:
        path = self._path(namespace, key)
        if path.exists():
            path.unlink()

    def clear_namespace(self, namespace: str) -> None:
        ns_dir = self.base_dir / namespace
        if not ns_dir.exists():
            return
        for file in ns_dir.glob("*.json"):
            file.unlink()

    def _path(self, namespace: str, key: str) -> Path:
        safe_key = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.base_dir / namespace / f"{safe_key}.json"