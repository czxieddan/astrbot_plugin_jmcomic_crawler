from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchAlbumItem:
    album_id: str
    name: str
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    keyword: str
    page: int
    items: List[SearchAlbumItem] = field(default_factory=list)


@dataclass
class ChapterSummary:
    chapter_id: str
    name: str


@dataclass
class AlbumDetail:
    album_id: str
    name: str
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    likes: Optional[str] = None
    page_count: Optional[int] = None
    chapters: List[ChapterSummary] = field(default_factory=list)


@dataclass
class ChapterDetail:
    chapter_id: str
    name: str
    album_id: Optional[str] = None
    album_name: Optional[str] = None
    image_count: Optional[int] = None
    publish_time: Optional[str] = None