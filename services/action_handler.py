from __future__ import annotations

from astrbot.api import logger

from .jm_service import JMQueryError


class ActionHandler:
    def __init__(
        self,
        query_usecase,
        summary_usecase,
        recommend_usecase,
        task_usecase,
    ):
        self.query_usecase = query_usecase
        self.summary_usecase = summary_usecase
        self.recommend_usecase = recommend_usecase
        self.task_usecase = task_usecase

    async def safe_call(self, action: str, coro) -> str:
        try:
            return await coro
        except JMQueryError as exc:
            logger.warning("JMComic %s 失败: %s", action, exc)
            return f"JMComic {action}失败：{exc}"
        except Exception as exc:
            logger.exception("JMComic %s 出现未处理异常: %s", action, exc)
            return f"JMComic {action}失败：发生未预期错误 {exc}"

    async def search(self, event, keyword: str, page: int = 1) -> str:
        return await self.query_usecase.search(event, keyword, page)

    async def album_detail(self, event, album_id: str | None) -> str:
        return await self.query_usecase.album_detail(event, album_id)

    async def chapter_detail(self, event, chapter_id: str | None) -> str:
        return await self.query_usecase.chapter_detail(event, chapter_id)

    async def album_comments(self, event, album_id: str | None, limit: int = 10) -> str:
        return await self.query_usecase.album_comments(event, album_id, limit)

    async def chapter_comments(self, event, chapter_id: str | None, limit: int = 10) -> str:
        return await self.query_usecase.chapter_comments(event, chapter_id, limit)

    async def analyze_album_sentiment(self, event, album_id: str | None, limit: int = 20) -> str:
        return await self.query_usecase.analyze_album_sentiment(event, album_id, limit)

    async def summarize_album(self, event, album_id: str | None) -> str:
        return await self.summary_usecase.summarize_album(event, album_id)

    async def summarize_chapter(self, event, chapter_id: str | None) -> str:
        return await self.summary_usecase.summarize_chapter(event, chapter_id)

    async def recommend(self, event, album_id: str | None) -> str:
        return await self.recommend_usecase.recommend(event, album_id)

    async def create_album_download_task(self, event, album_id: str | None, requested_by: str, create_zip: bool) -> str:
        return await self.task_usecase.create_album_download_task(event, album_id, requested_by, create_zip)

    async def create_chapter_download_task(self, event, chapter_id: str | None, requested_by: str, create_zip: bool) -> str:
        return await self.task_usecase.create_chapter_download_task(event, chapter_id, requested_by, create_zip)

    async def create_batch_album_download_task(self, event, album_ids: list[str], requested_by: str, create_zip: bool) -> str:
        return await self.task_usecase.create_batch_album_download_task(event, album_ids, requested_by, create_zip)

    async def list_tasks(self, event) -> str:
        return await self.task_usecase.list_tasks(event)

    async def get_task_status(self, event, task_id: str | None) -> str:
        return await self.task_usecase.get_task_status(event, task_id)

    async def cancel_task(self, event, task_id: str | None) -> str:
        return await self.task_usecase.cancel_task(event, task_id)