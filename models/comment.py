from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CommentItem:
    comment_id: str
    user_name: str
    content: str
    created_at: Optional[str] = None
    likes: Optional[int] = None
    reply_count: Optional[int] = None


@dataclass
class CommentResult:
    target_id: str
    target_type: str
    items: list[CommentItem] = field(default_factory=list)