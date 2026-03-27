from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigStateManager:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "runtime_state.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self, state: dict[str, Any]) -> None:
        self.path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update(self, **kwargs) -> dict[str, Any]:
        state = self.load()
        state.update(kwargs)
        self.save(state)
        return state