from __future__ import annotations

from ..jm_service import JMQueryError


class SummaryUseCase:
    def __init__(
        self,
        query_usecase,
        summary_service,
        response_builder,
        llm_response_service,
        sentiment_service=None,
    ):
        self.query_usecase = query_usecase
        self.summary_service = summary_service
        self.response_builder = response_builder
        self.llm_response_service = llm_response_service
        self.sentiment_service = sentiment_service

    async def summarize_album(self, event, album_id: str | None) -> str:
        resolved_album = self.query_usecase._resolve_album(event, album_id)
        if not resolved_album:
            raise JMQueryError("缺少 album_id")

        detail = await self.query_usecase.jm_service.get_album_detail(album_id=resolved_album)
        comments = await self.query_usecase.comment_service.get_album_comments(
            album_id=resolved_album,
            limit=10,
        )
        sentiment = (
            await self.sentiment_service.analyze_comments(comments)
            if self.sentiment_service is not None
            else None
        )
        payload = {
            "type": "album_summary",
            "detail": self.response_builder.album_payload(detail),
            "comments": self.response_builder.comments_payload(comments),
            "sentiment": sentiment,
        }
        fallback = await self.summary_service.summarize_album(detail, comments)
        self.query_usecase._remember_album(event, resolved_album)
        return await self.llm_response_service.polish(
            action="总结本子",
            payload=payload,
            fallback_text=fallback,
            event=event,
        )

    async def summarize_chapter(self, event, chapter_id: str | None) -> str:
        resolved_chapter = self.query_usecase._resolve_chapter(event, chapter_id)
        if not resolved_chapter:
            raise JMQueryError("缺少 chapter_id")

        detail = await self.query_usecase.jm_service.get_chapter_detail(chapter_id=resolved_chapter)
        comments = await self.query_usecase.comment_service.get_chapter_comments(
            chapter_id=resolved_chapter,
            limit=10,
        )
        sentiment = (
            await self.sentiment_service.analyze_comments(comments)
            if self.sentiment_service is not None
            else None
        )
        payload = {
            "type": "chapter_summary",
            "detail": self.response_builder.chapter_payload(detail),
            "comments": self.response_builder.comments_payload(comments),
            "sentiment": sentiment,
        }
        fallback = await self.summary_service.summarize_chapter(detail, comments)
        self.query_usecase._remember_chapter(event, resolved_chapter)
        return await self.llm_response_service.polish(
            action="总结章节",
            payload=payload,
            fallback_text=fallback,
            event=event,
        )