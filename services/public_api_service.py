from __future__ import annotations

from typing import Any


class PublicAPIService:
    def __init__(self, app):
        self.app = app

    async def search_album_structured(self, keyword: str, page: int = 1) -> dict[str, Any]:
        result = await self.app.service.search_album(keyword=keyword, page=page)
        return self.app.response_builder.search_payload(result)

    async def album_detail_structured(self, album_id: str) -> dict[str, Any]:
        result = await self.app.service.get_album_detail(album_id=album_id)
        return self.app.response_builder.album_payload(result)

    async def chapter_detail_structured(self, chapter_id: str) -> dict[str, Any]:
        result = await self.app.service.get_chapter_detail(chapter_id=chapter_id)
        return self.app.response_builder.chapter_payload(result)

    async def album_comments_structured(self, album_id: str, limit: int = 10) -> dict[str, Any]:
        comments = await self.app.comment_service.get_album_comments(album_id=album_id, limit=limit)
        return self.app.response_builder.comments_payload(comments)

    async def chapter_comments_structured(self, chapter_id: str, limit: int = 10) -> dict[str, Any]:
        comments = await self.app.comment_service.get_chapter_comments(chapter_id=chapter_id, limit=limit)
        return self.app.response_builder.comments_payload(comments)

    async def album_sentiment_structured(self, album_id: str, limit: int = 20) -> dict[str, Any]:
        comments = await self.app.comment_service.get_album_comments(album_id=album_id, limit=limit)
        return await self.app.sentiment_service.analyze_comments(comments)

    async def create_album_download_task_structured(
        self,
        album_id: str,
        requested_by: str | None = None,
        create_zip: bool = False,
    ) -> dict[str, Any]:
        return await self.app.download_service.create_album_download_task(
            album_id=album_id,
            requested_by=requested_by,
            create_zip=create_zip,
        )

    async def create_chapter_download_task_structured(
        self,
        chapter_id: str,
        requested_by: str | None = None,
        create_zip: bool = False,
    ) -> dict[str, Any]:
        return await self.app.download_service.create_chapter_download_task(
            chapter_id=chapter_id,
            requested_by=requested_by,
            create_zip=create_zip,
        )

    async def task_status_structured(self, task_id: str | None = None, event=None) -> dict[str, Any] | None:
        resolved = task_id
        if resolved is None and self.app.memory_service:
            resolved = self.app.memory_service.resolve_task(event, None)
        if not resolved:
            return None
        return self.app.task_manager.get_task(resolved)

    async def recommend_structured(self, album_id: str) -> dict[str, Any]:
        detail = await self.app.service.get_album_detail(album_id=album_id)
        keyword = detail.tags[0] if detail.tags else detail.name
        search_result = await self.app.service.search_album(keyword=keyword, page=1)
        comments = await self.app.comment_service.get_album_comments(album_id=album_id, limit=10)
        return {
            "source_album": self.app.response_builder.album_payload(detail),
            "search_candidates": self.app.response_builder.search_payload(search_result),
            "comments": self.app.response_builder.comments_payload(comments),
        }

    async def workflow_structured(
        self,
        goal: str,
        album_id: str | None = None,
        chapter_id: str | None = None,
        event=None,
    ) -> dict[str, Any]:
        return {
            "goal": goal,
            "album_id": album_id,
            "chapter_id": chapter_id,
            "memory": self.app.memory_service.get_memory(event) if self.app.memory_service else {},
        }

    async def search_album_text(self, event, keyword: str, page: int = 1) -> str:
        return await self.app.action_handler.search(event, keyword, page)

    async def album_detail_text(self, event, album_id: str) -> str:
        return await self.app.action_handler.album_detail(event, album_id)

    async def chapter_detail_text(self, event, chapter_id: str) -> str:
        return await self.app.action_handler.chapter_detail(event, chapter_id)

    async def album_comments_text(self, event, album_id: str, limit: int = 10) -> str:
        return await self.app.action_handler.album_comments(event, album_id, limit)

    async def chapter_comments_text(self, event, chapter_id: str, limit: int = 10) -> str:
        return await self.app.action_handler.chapter_comments(event, chapter_id, limit)

    async def album_summary_text(self, event, album_id: str) -> str:
        return await self.app.action_handler.summarize_album(event, album_id)

    async def chapter_summary_text(self, event, chapter_id: str) -> str:
        return await self.app.action_handler.summarize_chapter(event, chapter_id)

    async def recommend_text(self, event, album_id: str) -> str:
        return await self.app.action_handler.recommend(event, album_id)

    async def album_sentiment_text(self, event, album_id: str, limit: int = 20) -> str:
        return await self.app.action_handler.analyze_album_sentiment(event, album_id, limit)

    async def workflow_text(
        self,
        event,
        goal: str,
        album_id: str | None = None,
        chapter_id: str | None = None,
    ) -> str:
        return await self.app.workflow_service.run(event, goal, album_id, chapter_id)