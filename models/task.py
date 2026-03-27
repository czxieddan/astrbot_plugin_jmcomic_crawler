from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class DownloadTask:
    task_id: str
    task_type: str
    target_id: str
    status: str = "pending"
    progress: float = 0.0
    total_items: int = 0
    completed_items: int = 0
    save_path: Optional[str] = None
    zip_path: Optional[str] = None
    error_message: Optional[str] = None
    requested_by: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DownloadTask":
        return cls(**data)

    def touch(self) -> None:
        self.updated_at = now_iso()


@dataclass
class BatchDownloadTask:
    task_id: str
    task_type: str
    target_ids: list[str]
    status: str = "pending"
    progress: float = 0.0
    total_items: int = 0
    completed_items: int = 0
    child_task_ids: list[str] = field(default_factory=list)
    requested_by: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchDownloadTask":
        return cls(**data)

    def touch(self) -> None:
        self.updated_at = now_iso()