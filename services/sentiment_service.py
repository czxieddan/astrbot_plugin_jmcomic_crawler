from __future__ import annotations

from collections import Counter

from ..models.comment import CommentResult


class SentimentService:
    def __init__(self, config: dict):
        self.config = config or {}
        self.positive_words = {
            "好",
            "不错",
            "喜欢",
            "推荐",
            "香",
            "精彩",
            "优秀",
            "带劲",
            "好看",
            "赞",
        }
        self.negative_words = {
            "差",
            "烂",
            "无聊",
            "失望",
            "一般",
            "难看",
            "劝退",
            "糟糕",
            "重复",
            "水",
        }

    async def analyze_comments(self, comments: CommentResult) -> dict:
        items = comments.items
        if not items:
            return {
                "target_id": comments.target_id,
                "target_type": comments.target_type,
                "sample_count": 0,
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "top_positive_keywords": [],
                "top_negative_keywords": [],
                "summary": "评论样本不足，暂时无法分析情绪倾向。",
            }

        positive = 0
        negative = 0
        neutral = 0
        positive_counter = Counter()
        negative_counter = Counter()

        for item in items:
            tokens = self._tokenize(item.content)
            pos_hits = [word for word in tokens if word in self.positive_words]
            neg_hits = [word for word in tokens if word in self.negative_words]

            if len(pos_hits) > len(neg_hits):
                positive += 1
                positive_counter.update(pos_hits)
            elif len(neg_hits) > len(pos_hits):
                negative += 1
                negative_counter.update(neg_hits)
            else:
                neutral += 1

        sample_count = len(items)
        summary = self._build_summary(sample_count, positive, neutral, negative)

        return {
            "target_id": comments.target_id,
            "target_type": comments.target_type,
            "sample_count": sample_count,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "top_positive_keywords": [word for word, _ in positive_counter.most_common(5)],
            "top_negative_keywords": [word for word, _ in negative_counter.most_common(5)],
            "summary": summary,
        }

    def _build_summary(self, sample_count: int, positive: int, neutral: int, negative: int) -> str:
        if sample_count == 0:
            return "评论样本不足，暂时无法分析情绪倾向。"
        if positive > negative and positive >= neutral:
            return "整体评论风向偏正面，用户反馈相对积极。"
        if negative > positive and negative >= neutral:
            return "整体评论风向偏负面，存在较明显吐槽或不满。"
        return "整体评论风向偏中性，评价较分散或正负意见接近。"

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        separators = [",", "，", "。", "！", "?", "？", "、", "\n", "\t", " "]
        tokens = [text]
        for sep in separators:
            next_tokens = []
            for token in tokens:
                next_tokens.extend(token.split(sep))
            tokens = next_tokens
        return [token.strip() for token in tokens if token.strip()]