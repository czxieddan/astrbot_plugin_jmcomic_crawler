from __future__ import annotations

import asyncio
from typing import Any, Iterable, Optional

from models.dto import (
    AlbumDetail,
    ChapterDetail,
    ChapterSummary,
    SearchAlbumItem,
    SearchResult,
)


class JMQueryError(Exception):
    pass


class JMComicService:
    def __init__(self, config: dict, pool_service=None):
        self.config = config or {}
        self.pool_service = pool_service
        self._client = None
        self._module = None
        self._bundle_key = None

    async def close(self) -> None:
        client = getattr(self, "_client", None)
        if client is None:
            return

        close_fn = getattr(client, "close", None)
        if callable(close_fn):
            result = close_fn()
            if asyncio.iscoroutine(result):
                await result

    async def search_album(self, keyword: str, page: int = 1) -> SearchResult:
        if not keyword.strip():
            raise JMQueryError("搜索关键词不能为空")
        return await asyncio.to_thread(self._search_album_sync, keyword.strip(), page)

    async def get_album_detail(self, album_id: str) -> AlbumDetail:
        if not album_id.strip():
            raise JMQueryError("album_id 不能为空")
        return await asyncio.to_thread(self._get_album_detail_sync, album_id.strip())

    async def get_chapter_detail(self, chapter_id: str) -> ChapterDetail:
        if not chapter_id.strip():
            raise JMQueryError("chapter_id 不能为空")
        return await asyncio.to_thread(self._get_chapter_detail_sync, chapter_id.strip())

    def _load_module(self):
        if self._module is not None:
            return self._module
        try:
            import jmcomic  # type: ignore
        except ImportError as exc:
            raise JMQueryError("缺少 jmcomic 依赖，请确认已安装 requirements.txt 中的依赖") from exc
        self._module = jmcomic
        return jmcomic

    def _search_album_sync(self, keyword: str, page: int) -> SearchResult:
        return self._execute_with_failover(
            fn_candidates=("search_site", "search_album", "search"),
            invoke_args=(keyword,),
            invoke_kwargs={"page": page},
            normalize=lambda raw: self._normalize_search_result(keyword, page, raw),
            action_name="搜索接口",
        )

    def _get_album_detail_sync(self, album_id: str) -> AlbumDetail:
        return self._execute_with_failover(
            fn_candidates=("get_album_detail", "album_detail", "get_album", "fetch_album_detail"),
            invoke_args=(album_id,),
            invoke_kwargs={},
            normalize=lambda raw: self._normalize_album_detail(album_id, raw),
            action_name="本子详情接口",
        )

    def _get_chapter_detail_sync(self, chapter_id: str) -> ChapterDetail:
        return self._execute_with_failover(
            fn_candidates=("get_photo_detail", "get_chapter_detail", "chapter_detail", "get_chapter", "fetch_photo_detail"),
            invoke_args=(chapter_id,),
            invoke_kwargs={},
            normalize=lambda raw: self._normalize_chapter_detail(chapter_id, raw),
            action_name="章节详情接口",
        )

    def _execute_with_failover(
        self,
        fn_candidates: tuple[str, ...],
        invoke_args: tuple,
        invoke_kwargs: dict,
        normalize,
        action_name: str,
    ):
        jmcomic = self._load_module()
        attempts = self._max_attempts()
        last_error = None

        for _ in range(attempts):
            bundle = self._current_bundle()
            client = self._init_client(jmcomic, bundle)
            try:
                raw = self._invoke_candidates(client, fn_candidates, invoke_args, invoke_kwargs)
                if self.pool_service:
                    self.pool_service.mark_success()
                return normalize(raw)
            except Exception as exc:
                last_error = exc
                self._client = None
                self._bundle_key = None
                if self.pool_service:
                    self.pool_service.failover()
                else:
                    break

        raise JMQueryError(f"未能调用 jmcomic {action_name}: {last_error or '未找到可用方法'}")

    def _invoke_candidates(self, client, fn_candidates: tuple[str, ...], invoke_args: tuple, invoke_kwargs: dict):
        last_error = None
        for name in fn_candidates:
            fn = getattr(client, name, None)
            if not callable(fn):
                continue
            try:
                return fn(*invoke_args, **invoke_kwargs)
            except TypeError:
                try:
                    return fn(*invoke_args)
                except Exception as exc:
                    last_error = exc
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise JMQueryError("未找到可用方法")

    def _init_client(self, jmcomic, bundle: dict[str, Any]):
        bundle_key = self._bundle_identity(bundle)
        if self._client is not None and self._bundle_key == bundle_key:
            return self._client

        option = self._build_option(jmcomic, bundle)
        factory_names = ("create_client", "new_client", "JmcomicClient", "JMClient")
        for name in factory_names:
            factory = getattr(jmcomic, name, None)
            if factory is None:
                continue
            try:
                self._client = factory(option) if option is not None else factory()
                self._bundle_key = bundle_key
                return self._client
            except TypeError:
                try:
                    self._client = factory()
                    self._bundle_key = bundle_key
                    return self._client
                except Exception:
                    continue
            except Exception:
                continue

        self._client = jmcomic
        self._bundle_key = bundle_key
        return self._client

    def _build_option(self, jmcomic, bundle: dict[str, Any]) -> Optional[Any]:
        option = None
        for cls_name in ("JmOption", "JMOption"):
            cls = getattr(jmcomic, cls_name, None)
            if cls is None:
                continue
            try:
                option = cls.default() if hasattr(cls, "default") else cls()
                break
            except Exception:
                continue

        if option is None:
            return None

        domain = bundle.get("domain")
        proxy = bundle.get("proxy")
        account = bundle.get("account") or {}

        self._set_option_value(option, "proxies", proxy)
        self._set_option_value(option, "proxy", proxy)
        self._set_option_value(option, "domain", domain)
        self._set_option_value(option, "base_url", domain)

        username = account.get("username")
        password = account.get("password")
        if username and password:
            self._set_option_value(option, "username", username)
            self._set_option_value(option, "password", password)
            for method_name in ("set_login", "set_user", "login"):
                method = getattr(option, method_name, None)
                if callable(method):
                    try:
                        method(username, password)
                        break
                    except Exception:
                        continue

        return option

    def _current_bundle(self) -> dict[str, Any]:
        if self.pool_service:
            return self.pool_service.get_current_bundle()

        account = None
        username = self.config.get("jm_username")
        password = self.config.get("jm_password")
        if username and password:
            account = {"username": username, "password": password}

        return {
            "account": account,
            "domain": self.config.get("domain"),
            "proxy": self.config.get("proxies"),
        }

    def _max_attempts(self) -> int:
        if not self.pool_service:
            return 1

        accounts = max(1, len(self.pool_service.account_pool))
        domains = max(1, len(self.pool_service.domain_pool))
        proxies = max(1, len(self.pool_service.proxy_pool))
        return max(1, accounts * domains * proxies)

    @staticmethod
    def _bundle_identity(bundle: dict[str, Any]) -> tuple:
        account = bundle.get("account") or {}
        return (
            account.get("username"),
            account.get("password"),
            bundle.get("domain"),
            bundle.get("proxy"),
        )

    @staticmethod
    def _set_option_value(option: Any, key: str, value: Any) -> None:
        if value in (None, "", {}):
            return

        if hasattr(option, key):
            try:
                setattr(option, key, value)
                return
            except Exception:
                pass

        for container_name in ("client", "network", "plugins", "download"):
            container = getattr(option, container_name, None)
            if container is not None and hasattr(container, key):
                try:
                    setattr(container, key, value)
                    return
                except Exception:
                    continue

    def _normalize_search_result(self, keyword: str, page: int, raw: Any) -> SearchResult:
        items: list[SearchAlbumItem] = []
        candidates = raw
        if isinstance(raw, dict):
            candidates = raw.get("content") or raw.get("items") or raw.get("data") or raw.get("list") or []
        elif hasattr(raw, "content"):
            candidates = getattr(raw, "content")
        elif hasattr(raw, "items"):
            candidates = getattr(raw, "items")

        for item in self._iter_items(candidates):
            album_id = self._pick_first(item, ("album_id", "id"))
            name = self._pick_first(item, ("name", "title"))
            if not album_id or not name:
                continue
            author = self._pick_first(item, ("author", "authors"))
            tags = self._normalize_tags(self._pick_first(item, ("tags", "tag_list", "works")))
            items.append(
                SearchAlbumItem(
                    album_id=str(album_id),
                    name=str(name),
                    author=str(author) if author else None,
                    tags=tags,
                )
            )

        max_results = int(self.config.get("max_search_results", 5) or 5)
        return SearchResult(keyword=keyword, page=page, items=items[:max_results])

    def _normalize_album_detail(self, album_id: str, raw: Any) -> AlbumDetail:
        name = self._pick_first(raw, ("name", "title")) or f"album_{album_id}"
        author = self._pick_first(raw, ("author", "authors"))
        tags = self._normalize_tags(self._pick_first(raw, ("tags", "tag_list", "works")))
        description = self._pick_first(raw, ("description", "comment", "intro"))
        likes = self._pick_first(raw, ("likes", "like_count"))
        page_count = self._pick_first(raw, ("page_count", "images", "image_count"))

        chapters: list[ChapterSummary] = []
        for chapter in self._iter_items(self._pick_first(raw, ("chapters", "episode_list"))):
            chapter_id = self._pick_first(chapter, ("chapter_id", "photo_id", "id"))
            chapter_name = self._pick_first(chapter, ("name", "title"))
            if chapter_id and chapter_name:
                chapters.append(ChapterSummary(chapter_id=str(chapter_id), name=str(chapter_name)))

        page_count_int: Optional[int] = None
        if page_count is not None:
            try:
                page_count_int = int(page_count)
            except Exception:
                page_count_int = None

        return AlbumDetail(
            album_id=str(album_id),
            name=str(name),
            author=str(author) if author else None,
            tags=tags,
            description=str(description) if description else None,
            likes=str(likes) if likes else None,
            page_count=page_count_int,
            chapters=chapters,
        )

    def _normalize_chapter_detail(self, chapter_id: str, raw: Any) -> ChapterDetail:
        name = self._pick_first(raw, ("name", "title")) or f"chapter_{chapter_id}"
        album_id = self._pick_first(raw, ("album_id", "series_id"))
        album_name = self._pick_first(raw, ("album_name", "series_name"))
        publish_time = self._pick_first(raw, ("publish_time", "created_at", "pub_date"))

        images = self._pick_first(raw, ("images", "page_arr", "image_list"))
        image_count = None
        if images is not None:
            try:
                image_count = len(list(images))
            except Exception:
                image_count = None
        if image_count is None:
            count_value = self._pick_first(raw, ("image_count", "page_count"))
            if count_value is not None:
                try:
                    image_count = int(count_value)
                except Exception:
                    image_count = None

        return ChapterDetail(
            chapter_id=str(chapter_id),
            name=str(name),
            album_id=str(album_id) if album_id else None,
            album_name=str(album_name) if album_name else None,
            image_count=image_count,
            publish_time=str(publish_time) if publish_time else None,
        )

    @staticmethod
    def _iter_items(value: Any) -> Iterable[Any]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return value
        if isinstance(value, dict):
            return value.values()
        return [value]

    @staticmethod
    def _pick_first(obj: Any, keys: tuple[str, ...]) -> Any:
        for key in keys:
            if isinstance(obj, dict) and key in obj:
                return obj[key]
            if hasattr(obj, key):
                return getattr(obj, key)
        return None

    @staticmethod
    def _normalize_tags(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [tag.strip() for tag in value.split() if tag.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(tag).strip() for tag in value if str(tag).strip()]
        return [str(value).strip()]