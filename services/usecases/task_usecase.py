from __future__ import annotations

from ..jm_service import JMQueryError


class TaskUseCase:
    def __init__(
        self,
        query_usecase,
        download_service,
        task_manager,
        response_builder,
        llm_response_service,
        memory_service=None,
    ):
        self.query_usecase = query_usecase
        self.download_service = download_service
        self.task_manager = task_manager
        self.response_builder = response_builder
        self.llm_response_service = llm_response_service
        self.memory_service = memory_service

    async def create_album_download_task(self, event, album_id: str | None, requested_by: str, create_zip: bool) -> str:
        resolved_album = self.query_usecase._resolve_album(event, album_id)
        if not resolved_album:
            raise JMQueryError("缺少 album_id")

        task = await self.download_service.create_album_download_task(
            album_id=resolved_album,
            requested_by=requested_by,
            create_zip=create_zip,
        )
        self.query_usecase._remember_album(event, resolved_album)
        if self.memory_service:
            self.memory_service.remember_task(event, task.get("task_id"))
        return await self.llm_response_service.polish(
            action="创建本子下载任务",
            payload=self.response_builder.task_payload(task),
            fallback_text=self.response_builder.render_task(task),
            event=event,
        )

    async def create_chapter_download_task(self, event, chapter_id: str | None, requested_by: str, create_zip: bool) -> str:
        resolved_chapter = self.query_usecase._resolve_chapter(event, chapter_id)
        if not resolved_chapter:
            raise JMQueryError("缺少 chapter_id")

        task = await self.download_service.create_chapter_download_task(
            chapter_id=resolved_chapter,
            requested_by=requested_by,
            create_zip=create_zip,
        )
        self.query_usecase._remember_chapter(event, resolved_chapter)
        if self.memory_service:
            self.memory_service.remember_task(event, task.get("task_id"))
        return await self.llm_response_service.polish(
            action="创建章节下载任务",
            payload=self.response_builder.task_payload(task),
            fallback_text=self.response_builder.render_task(task),
            event=event,
        )

    async def create_batch_album_download_task(self, event, album_ids: list[str], requested_by: str, create_zip: bool) -> str:
        task = await self.download_service.create_batch_album_download_task(
            album_ids=album_ids,
            requested_by=requested_by,
            create_zip=create_zip,
        )
        if album_ids:
            self.query_usecase._remember_album(event, album_ids[0])
        if self.memory_service:
            self.memory_service.remember_task(event, task.get("task_id"))
        return await self.llm_response_service.polish(
            action="创建批量下载任务",
            payload=self.response_builder.task_payload(task),
            fallback_text=self.response_builder.render_task(task),
            event=event,
        )

    async def list_tasks(self, event) -> str:
        tasks = self.task_manager.list_tasks()
        return await self.llm_response_service.polish(
            action="列出下载任务",
            payload=self.response_builder.task_list_payload(tasks),
            fallback_text=self.response_builder.render_task_list(tasks),
            event=event,
        )

    async def get_task_status(self, event, task_id: str | None) -> str:
        resolved_task = self.memory_service.resolve_task(event, task_id) if self.memory_service else task_id
        if not resolved_task:
            return "未找到该任务。"

        task = self.task_manager.get_task(resolved_task)
        if not task:
            return "未找到该任务。"
        if self.memory_service:
            self.memory_service.remember_task(event, resolved_task)
        return await self.llm_response_service.polish(
            action="查询任务状态",
            payload=self.response_builder.task_payload(task),
            fallback_text=self.response_builder.render_task(task),
            event=event,
        )

    async def cancel_task(self, event, task_id: str | None) -> str:
        resolved_task = self.memory_service.resolve_task(event, task_id) if self.memory_service else task_id
        if not resolved_task:
            return "未找到该任务。"

        task = self.task_manager.cancel_task(resolved_task)
        if not task:
            return "未找到该任务。"
        if self.memory_service:
            self.memory_service.remember_task(event, resolved_task)
        return await self.llm_response_service.polish(
            action="取消下载任务",
            payload=self.response_builder.task_payload(task),
            fallback_text=self.response_builder.render_task(task),
            event=event,
        )