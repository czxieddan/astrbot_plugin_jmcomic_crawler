from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from models.task import BatchDownloadTask, DownloadTask, now_iso


class TaskManager:
    def __init__(self, data_dir: str):
        self.base_dir = Path(data_dir)
        self.tasks_dir = self.base_dir / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def create_download_task(
        self,
        task_type: str,
        target_id: str,
        requested_by: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> DownloadTask:
        task = DownloadTask(
            task_id=self._new_task_id(),
            task_type=task_type,
            target_id=target_id,
            requested_by=requested_by,
            extra=extra or {},
        )
        self.save_download_task(task)
        return task

    def create_batch_task(
        self,
        task_type: str,
        target_ids: list[str],
        requested_by: Optional[str] = None,
    ) -> BatchDownloadTask:
        task = BatchDownloadTask(
            task_id=self._new_task_id(),
            task_type=task_type,
            target_ids=target_ids,
            requested_by=requested_by,
            total_items=len(target_ids),
        )
        self.save_batch_task(task)
        return task

    def get_task(self, task_id: str) -> Optional[dict]:
        path = self.tasks_dir / f"{task_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_tasks(self, limit: int = 20) -> list[dict]:
        files = sorted(
            self.tasks_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        result = []
        for path in files[:limit]:
            result.append(json.loads(path.read_text(encoding="utf-8")))
        return result

    def save_download_task(self, task: DownloadTask) -> None:
        task.touch()
        self._write_task_file(task.task_id, task.to_dict())

    def save_batch_task(self, task: BatchDownloadTask) -> None:
        task.touch()
        self._write_task_file(task.task_id, task.to_dict())

    def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[float] = None,
        completed_items: Optional[int] = None,
        total_items: Optional[int] = None,
        error_message: Optional[str] = None,
        save_path: Optional[str] = None,
        zip_path: Optional[str] = None,
    ) -> Optional[dict]:
        task = self.get_task(task_id)
        if not task:
            return None

        task["status"] = status
        task["updated_at"] = now_iso()
        if progress is not None:
            task["progress"] = progress
        if completed_items is not None:
            task["completed_items"] = completed_items
        if total_items is not None:
            task["total_items"] = total_items
        if error_message is not None:
            task["error_message"] = error_message
        if save_path is not None:
            task["save_path"] = save_path
        if zip_path is not None:
            task["zip_path"] = zip_path

        self._write_task_file(task_id, task)
        return task

    def cancel_task(self, task_id: str) -> Optional[dict]:
        return self.update_task_status(task_id=task_id, status="cancelled")

    def _write_task_file(self, task_id: str, data: dict) -> None:
        path = self.tasks_dir / f"{task_id}.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _new_task_id() -> str:
        return uuid.uuid4().hex[:12]