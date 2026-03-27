from __future__ import annotations

import asyncio
from typing import Any

from ..models.comment import CommentItem, CommentResult
from .jm_service import JMComicService, JMQueryError


class CommentService:
    def __init__(self, config: dict, jm_service: JMComicService):
        self.config = config or {}
        self.jm_service = jm_service

    async def get_album_comments(self, album_id: str, limit: int = 10) -> CommentResult:
        return await asyncio.to_thread(
            self._get_comments_sync,
            "album",
            album_id,
            limit,
        )

    async def get_chapter_comments(self, chapter_id: str, limit: int = 10) -> CommentResult:
        return await asyncio.to_thread(
            self._get_comments_sync,
            "chapter",
            chapter_id,
            limit,
        )

    def _get_comments_sync(self, target_type: str, target_id: str, limit: int) -> CommentResult:
        client = self.jm_service._init_client()
        method_names = (
            "get_comments",
            "fetch_comments",
            "get_album_comments" if target_type == "album" else "get_chapter_comments",
            "get_photo_comments" if target_type == "chapter" else "get_comments_by_album",
        )

        last_error = None
        for method_name in method_names:
            method = getattr(client, method_name, None)
            if not callable(method):
                continue
            try:
                if "album" in method_name:
                    raw = method(target_id, limit=limit)
                elif "chapter" in method_name or "photo" in method_name:
                    raw = method(target_id, limit=limit)
                else:
                    raw = method(target_type, target_id, limit=limit)
                return self._normalize_comments(target_type, target_id, raw, limit)
            except TypeError:
                try:
                    raw = method(target_id)
                    return self._normalize_comments(target_type, target_id, raw, limit)
                except Exception as exc:
                    last_error = exc
            except Exception as exc:
                last_error = exc

        if self.config.get("comments_enabled", True):
            return CommentResult(
                target_id=target_id,
                target_type=target_type,
                items=[
                    CommentItem(
                        comment_id="placeholder-1",
                        user_name="system",
                        content=(
                            "当前 jmcomic 版本未暴露通用评论接口，"
                            "已返回占位评论结果。后续可按实际库 API 补充适配。"
                        ),
                    )
                ],
            )

        raise JMQueryError(f"评论功能未启用或不可用: {last_error or '未找到评论接口'}")

    def _normalize_comments(
        self,
        target_type: str,
        target_id: str,
        raw: Any,
        limit: int,
    ) -> CommentResult:
        items_raw = raw
        if isinstance(raw, dict):
            items_raw = raw.get("comments") or raw.get("items") or raw.get("data") or []
        elif hasattr(raw, "comments"):
            items_raw = getattr(raw, "comments")
        elif hasattr(raw, "items"):
            items_raw = getattr(raw, "items")

        result_items: list[CommentItem] = []
        iterable = items_raw if isinstance(items_raw, (list, tuple, set)) else [items_raw]
        for idx, item in enumerate(iterable):
            if idx >= limit:
                break
            comment_id = self._pick(item, ("comment_id", "id")) or f"comment-{idx + 1}"
            user_name = self._pick(item, ("user_name", "username", "nickname")) or "unknown"
            content = self._pick(item, ("content", "text", "comment")) or ""
            created_at = self._pick(item, ("created_at", "time", "publish_time"))
            likes = self._pick(item, ("likes", "like_count"))
            reply_count = self._pick(item, ("reply_count", "replies"))

            try:
                likes = int(likes) if likes is not None else None
            except Exception:
                likes = None

            try:
                reply_count = int(reply_count) if reply_count is not None else None
            except Exception:
                reply_count = None

            result_items.append(
                CommentItem(
                    comment_id=str(comment_id),
                    user_name=str(user_name),
                    content=str(content),
                    created_at=str(created_at) if created_at else None,
                    likes=likes,
                    reply_count=reply_count,
                )
            )

        return CommentResult(
            target_id=target_id,
            target_type=target_type,
            items=result_items,
        )

    @staticmethod
    def _pick(obj: Any, keys: tuple[str, ...]) -> Any:
        for key in keys:
            if isinstance(obj, dict) and key in obj:
                return obj[key]
            if hasattr(obj, key):
                return getattr(obj, key)
        return None