from __future__ import annotations

from collections import Counter

from ..models.comment import CommentResult
from ..models.dto import AlbumDetail, ChapterDetail


class SummaryService:
    def __init__(self, config: dict):
        self.config = config or {}

    async def summarize_album(self, detail: AlbumDetail, comments: CommentResult | None = None) -> str:
        lines = [
            "JM 本子总结",
            f"- 标题: {detail.name}",
            f"- 作者: {detail.author or '未知'}",
            f"- 标签: {' / '.join(detail.tags) if detail.tags else '无'}",
            f"- 章节数: {len(detail.chapters)}",
            f"- 页数: {detail.page_count or '未知'}",
        ]

        if detail.description:
            lines.append(f"- 简介总结: {self._compress_text(detail.description)}")

        if comments and comments.items:
            lines.append(f"- 评论数(已采样): {len(comments.items)}")
            lines.append(f"- 评论风向: {self._summarize_comments(comments)}")

        lines.append(
            "- 综合结论: 该作品的主要特征来自标题、标签、章节信息与评论采样；"
            "如需更高质量语义总结，可在后续版本接入 AstrBot 当前会话 LLM。"
        )
        return "\n".join(lines)

    async def summarize_chapter(
        self,
        detail: ChapterDetail,
        comments: CommentResult | None = None,
    ) -> str:
        lines = [
            "JM 章节总结",
            f"- 标题: {detail.name}",
            f"- chapter_id: {detail.chapter_id}",
            f"- 所属本子: {detail.album_name or '未知'}",
            f"- 图片数量: {detail.image_count if detail.image_count is not None else '未知'}",
        ]

        if comments and comments.items:
            lines.append(f"- 评论风向: {self._summarize_comments(comments)}")

        lines.append("- 综合结论: 当前为规则型总结结果，可继续升级为 LLM 摘要版本。")
        return "\n".join(lines)

    def _summarize_comments(self, comments: CommentResult) -> str:
        words: list[str] = []
        for item in comments.items:
            words.extend(self._tokenize(item.content))

        if not words:
            return "评论内容较少，暂无法提炼稳定观点。"

        counter = Counter(words)
        top_words = [word for word, _ in counter.most_common(8)]
        return f"高频关键词：{' / '.join(top_words)}"

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        seps = [",", "，", "。", "！", "?", "？", "、", "\n", "\t", " "]
        tokens = [text]
        for sep in seps:
            next_tokens = []
            for token in tokens:
                next_tokens.extend(token.split(sep))
            tokens = next_tokens
        return [token.strip() for token in tokens if len(token.strip()) >= 2][:50]

    @staticmethod
    def _compress_text(text: str, max_len: int = 120) -> str:
        text = " ".join(text.split())
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."