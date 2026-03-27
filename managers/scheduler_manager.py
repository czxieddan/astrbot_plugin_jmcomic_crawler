from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Optional


class SchedulerManager:
    def __init__(self, max_concurrency: int = 2):
        self.max_concurrency = max(1, int(max_concurrency or 1))
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        self.running_tasks: dict[str, asyncio.Task] = {}
        self.cancelled: set[str] = set()

    async def run(
        self,
        task_id: str,
        runner: Callable[[], Awaitable[None]],
    ) -> None:
        async with self.semaphore:
            if task_id in self.cancelled:
                return
            current = asyncio.current_task()
            if current is not None:
                self.running_tasks[task_id] = current
            try:
                await runner()
            finally:
                self.running_tasks.pop(task_id, None)

    def create_background_task(
        self,
        task_id: str,
        runner: Callable[[], Awaitable[None]],
    ) -> asyncio.Task:
        task = asyncio.create_task(self.run(task_id, runner))
        self.running_tasks[task_id] = task
        return task

    def cancel(self, task_id: str) -> bool:
        self.cancelled.add(task_id)
        task = self.running_tasks.get(task_id)
        if task is None:
            return False
        task.cancel()
        return True

    def is_cancelled(self, task_id: str) -> bool:
        return task_id in self.cancelled

    def get_running_task_ids(self) -> list[str]:
        return list(self.running_tasks.keys())