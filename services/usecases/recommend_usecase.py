from __future__ import annotations

from ..jm_service import JMQueryError


class RecommendUseCase:
    def __init__(
        self,
        query_usecase,
        recommend_service,
        response_builder,
        llm_response_service,
        sentiment_service=None,
    ):
        self.query_usecase = query_usecase
        self.recommend_service = recommend_service
        self.response_builder = response_builder
        self.llm_response_service = llm_response_service
        self.sentiment_service = sentiment_service

    async def recommend(self, event, album_id: str | None) -> str:
        resolved_album = self.query_usecase._resolve_album(event, album_id)
        if not resolved_album:
            raise JMQueryError("缺少 album_id")

        detail = await self.query_usecase.jm_service.get_album_detail(album_id=resolved_album)
        keyword = detail.tags[0] if detail.tags else detail.name
        search_result = await self.query_usecase.jm_service.search_album(keyword=keyword, page=1)
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
            "type": "recommendation",
            "source_album": self.response_builder.album_payload(detail),
            "search_candidates": self.response_builder.search_payload(search_result),
            "comments": self.response_builder.comments_payload(comments),
            "sentiment": sentiment,
        }
        fallback = await self.recommend_service.recommend_similar_albums(detail, search_result, comments)
        self.query_usecase._remember_album(event, resolved_album)
        return await self.llm_response_service.polish(
            action="推荐相似作品",
            payload=payload,
            fallback_text=fallback,
            event=event,
        )