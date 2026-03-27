from __future__ import annotations

from ..jm_service import JMQueryError


class QueryUseCase:
    def __init__(
        self,
        jm_service,
        comment_service,
        sentiment_service,
        response_builder,
        llm_response_service,
        cache_manager=None,
        memory_service=None,
    ):
        self.jm_service = jm_service
        self.comment_service = comment_service
        self.sentiment_service = sentiment_service
        self.response_builder = response_builder
        self.llm_response_service = llm_response_service
        self.cache_manager = cache_manager
        self.memory_service = memory_service

    async def search(self, event, keyword: str, page: int = 1) -> str:
        cache_key = f"{keyword}:{page}"
        ttl = int(getattr(self.jm_service, "config", {}).get("cache_ttl_seconds", 300) or 300)
        cached = self._cache_get("search", cache_key, ttl)
        if cached:
            return cached

        result = await self.jm_service.search_album(keyword=keyword, page=page)
        text = await self._finalize(
            event,
            "搜索本子",
            self.response_builder.search_payload(result),
            self.response_builder.render_search_result(result),
        )
        self._cache_set("search", cache_key, text, ttl)
        return text

    async def album_detail(self, event, album_id: str | None) -> str:
        resolved_album = self._resolve_album(event, album_id)
        if not resolved_album:
            raise JMQueryError("缺少 album_id")

        ttl = int(getattr(self.jm_service, "config", {}).get("cache_ttl_seconds", 300) or 300)
        cached = self._cache_get("album_detail", resolved_album, ttl)
        if cached:
            self._remember_album(event, resolved_album)
            return cached

        result = await self.jm_service.get_album_detail(album_id=resolved_album)
        text = await self._finalize(
            event,
            "查询本子详情",
            self.response_builder.album_payload(result),
            self.response_builder.render_album_detail(result),
        )
        self._remember_album(event, resolved_album)
        self._cache_set("album_detail", resolved_album, text, ttl)
        return text

    async def chapter_detail(self, event, chapter_id: str | None) -> str:
        resolved_chapter = self._resolve_chapter(event, chapter_id)
        if not resolved_chapter:
            raise JMQueryError("缺少 chapter_id")

        ttl = int(getattr(self.jm_service, "config", {}).get("cache_ttl_seconds", 300) or 300)
        cached = self._cache_get("chapter_detail", resolved_chapter, ttl)
        if cached:
            self._remember_chapter(event, resolved_chapter)
            return cached

        result = await self.jm_service.get_chapter_detail(chapter_id=resolved_chapter)
        text = await self._finalize(
            event,
            "查询章节详情",
            self.response_builder.chapter_payload(result),
            self.response_builder.render_chapter_detail(result),
        )
        self._remember_chapter(event, resolved_chapter)
        self._cache_set("chapter_detail", resolved_chapter, text, ttl)
        return text

    async def album_comments(self, event, album_id: str | None, limit: int = 10) -> str:
        resolved_album = self._resolve_album(event, album_id)
        if not resolved_album:
            raise JMQueryError("缺少 album_id")

        ttl = int(getattr(self.jm_service, "config", {}).get("cache_ttl_seconds", 300) or 300)
        cache_key = f"{resolved_album}:{limit}"
        cached = self._cache_get("album_comments", cache_key, ttl)
        if cached:
            self._remember_album(event, resolved_album)
            return cached

        comments = await self.comment_service.get_album_comments(album_id=resolved_album, limit=limit)
        text = await self._finalize(
            event,
            "读取本子评论",
            self.response_builder.comments_payload(comments),
            self.response_builder.render_comments(comments),
        )
        self._remember_album(event, resolved_album)
        self._cache_set("album_comments", cache_key, text, ttl)
        return text

    async def chapter_comments(self, event, chapter_id: str | None, limit: int = 10) -> str:
        resolved_chapter = self._resolve_chapter(event, chapter_id)
        if not resolved_chapter:
            raise JMQueryError("缺少 chapter_id")

        ttl = int(getattr(self.jm_service, "config", {}).get("cache_ttl_seconds", 300) or 300)
        cache_key = f"{resolved_chapter}:{limit}"
        cached = self._cache_get("chapter_comments", cache_key, ttl)
        if cached:
            self._remember_chapter(event, resolved_chapter)
            return cached

        comments = await self.comment_service.get_chapter_comments(chapter_id=resolved_chapter, limit=limit)
        text = await self._finalize(
            event,
            "读取章节评论",
            self.response_builder.comments_payload(comments),
            self.response_builder.render_comments(comments),
        )
        self._remember_chapter(event, resolved_chapter)
        self._cache_set("chapter_comments", cache_key, text, ttl)
        return text

    async def analyze_album_sentiment(self, event, album_id: str | None, limit: int = 20) -> str:
        if self.sentiment_service is None:
            return "当前未启用评论情感分析能力。"

        resolved_album = self._resolve_album(event, album_id)
        if not resolved_album:
            raise JMQueryError("缺少 album_id")

        comments = await self.comment_service.get_album_comments(album_id=resolved_album, limit=limit)
        analysis = await self.sentiment_service.analyze_comments(comments)
        payload = {"type": "sentiment_analysis", "analysis": analysis}
        fallback = "\n".join(
            [
                "评论情感分析",
                f"- sample_count: {analysis['sample_count']}",
                f"- positive: {analysis['positive']}",
                f"- neutral: {analysis['neutral']}",
                f"- negative: {analysis['negative']}",
                f"- summary: {analysis['summary']}",
                f"- top_positive_keywords: {' / '.join(analysis['top_positive_keywords']) or '无'}",
                f"- top_negative_keywords: {' / '.join(analysis['top_negative_keywords']) or '无'}",
            ]
        )
        self._remember_album(event, resolved_album)
        return await self._finalize(event, "评论情感分析", payload, fallback)

    def _resolve_album(self, event, album_id: str | None) -> str | None:
        if self.memory_service:
            return self.memory_service.resolve_album(event, album_id)
        return album_id

    def _resolve_chapter(self, event, chapter_id: str | None) -> str | None:
        if self.memory_service:
            return self.memory_service.resolve_chapter(event, chapter_id)
        return chapter_id

    def _remember_album(self, event, album_id: str) -> None:
        if self.memory_service:
            self.memory_service.remember_album(event, album_id)

    def _remember_chapter(self, event, chapter_id: str) -> None:
        if self.memory_service:
            self.memory_service.remember_chapter(event, chapter_id)

    def _cache_get(self, namespace: str, key: str, ttl: int | None = None):
        if self.cache_manager is None:
            return None
        return self.cache_manager.get(namespace, key, ttl)

    def _cache_set(self, namespace: str, key: str, value, ttl: int | None = None) -> None:
        if self.cache_manager is None:
            return
        self.cache_manager.set(namespace, key, value, ttl)

    async def _finalize(self, event, action: str, payload: dict, fallback_text: str) -> str:
        return await self.llm_response_service.polish(
            action=action,
            payload=payload,
            fallback_text=fallback_text,
            event=event,
        )