from __future__ import annotations

from models.comment import CommentResult
from models.dto import AlbumDetail, SearchResult


class RecommendService:
    def __init__(self, config: dict):
        self.config = config or {}

    async def recommend_similar_albums(
        self,
        source_detail: AlbumDetail,
        search_result: SearchResult,
        comments: CommentResult | None = None,
    ) -> str:
        max_results = int(self.config.get("recommend_max_results", 5) or 5)
        source_tags = set(source_detail.tags)
        comment_keywords = self._extract_comment_keywords(comments) if comments else set()

        scored: list[tuple[int, object, list[str]]] = []
        for item in search_result.items:
            if item.album_id == source_detail.album_id:
                continue

            score = 0
            reasons: list[str] = []

            item_tags = set(item.tags)
            tag_overlap = source_tags.intersection(item_tags)
            if tag_overlap:
                overlap_score = min(len(tag_overlap) * 3, 12)
                score += overlap_score
                reasons.append(f"标签重合: {' / '.join(sorted(tag_overlap)[:4])}")

            if source_detail.author and item.author and source_detail.author == item.author:
                score += 5
                reasons.append("作者相同")

            keyword_overlap = comment_keywords.intersection(item_tags)
            if keyword_overlap:
                overlap_score = min(len(keyword_overlap) * 2, 8)
                score += overlap_score
                reasons.append(f"评论关键词相关: {' / '.join(sorted(keyword_overlap)[:4])}")

            if source_detail.name and item.name:
                name_tokens = self._split_keywords(source_detail.name)
                title_hits = name_tokens.intersection(self._split_keywords(item.name))
                if title_hits:
                    score += min(len(title_hits), 3)
                    reasons.append(f"标题关键词相近: {' / '.join(sorted(title_hits)[:3])}")

            if score > 0:
                scored.append((score, item, reasons))

        scored.sort(key=lambda x: x[0], reverse=True)
        recommendations = scored[:max_results]

        if not recommendations:
            return (
                "未生成稳定的相似作品推荐。建议扩大搜索关键词、补充评论样本，"
                "或后续接入更强的召回与排序策略。"
            )

        lines = ["JM 相似作品推荐"]
        for idx, (score, item, reasons) in enumerate(recommendations, start=1):
            lines.append(
                "\n".join(
                    [
                        f"{idx}. {item.name}",
                        f"   album_id: {item.album_id}",
                        f"   author: {item.author or '未知'}",
                        f"   score: {score}",
                        f"   理由: {'；'.join(reasons)}",
                    ]
                )
            )
        return "\n".join(lines)

    @staticmethod
    def _extract_comment_keywords(comments: CommentResult | None) -> set[str]:
        if not comments:
            return set()

        result = set()
        for item in comments.items:
            result.update(RecommendService._split_keywords(item.content))
        return result

    @staticmethod
    def _split_keywords(text: str) -> set[str]:
        normalized = text
        for sep in ["，", "。", ",", ".", "、", "\n", "\t", " "]:
            normalized = normalized.replace(sep, " ")
        return {token.strip() for token in normalized.split() if len(token.strip()) >= 2}