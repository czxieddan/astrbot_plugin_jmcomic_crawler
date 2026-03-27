from __future__ import annotations

import asyncio
import inspect
from typing import Any, Iterable, Optional

from ..models.dto import (
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
            invoker=lambda client, candidates, args, kwargs: self._invoke_search_candidates(
                client,
                candidates,
                keyword=keyword,
                page=page,
                jmcomic=self._module,
            ),
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
        invoker=None,
    ):
        jmcomic = self._load_module()
        attempts = self._max_attempts()
        last_error = None

        for _ in range(attempts):
            bundle = self._current_bundle()
            client = self._init_client(jmcomic, bundle)
            try:
                raw = (
                    invoker(client, fn_candidates, invoke_args, invoke_kwargs)
                    if callable(invoker)
                    else self._invoke_candidates(client, fn_candidates, invoke_args, invoke_kwargs)
                )
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

        error_text = "未找到可用方法"
        if last_error is not None:
            error_text = str(last_error).strip() or repr(last_error)
        raise JMQueryError(f"未能调用 jmcomic {action_name}: {error_text}")

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

    def _invoke_search_candidates(
        self,
        client,
        fn_candidates: tuple[str, ...],
        keyword: str,
        page: int,
        jmcomic=None,
    ):
        last_error = None
        try:
            main_tag = int(self.config.get("jm_search_main_tag", 0) or 0)
        except Exception:
            main_tag = 0
        order_by = str(self.config.get("jm_search_order_by", "") or "")
        time_filter = str(self.config.get("jm_search_time", "") or "")
        category = str(self.config.get("jm_search_category", "") or "")
        raw_sub_category = self.config.get("jm_search_sub_category", None)
        sub_category = None if raw_sub_category in (None, "") else str(raw_sub_category)

        for target_name, target in self._iter_search_targets(client, jmcomic):
            for name in fn_candidates:
                fn = getattr(target, name, None)
                if not callable(fn):
                    continue

                try:
                    signature = inspect.signature(fn)
                except Exception:
                    signature = None

                dynamic_attempt = self._build_search_attempt(
                    fn,
                    signature,
                    keyword,
                    page,
                    main_tag,
                    order_by,
                    time_filter,
                    category,
                    sub_category,
                )
                attempts = [dynamic_attempt] if dynamic_attempt is not None else []
                attempts.extend(
                    [
                        lambda: fn(keyword, page=page),
                        lambda: fn(keyword, page),
                        lambda: fn(
                            keyword,
                            page,
                            main_tag,
                            order_by,
                            time_filter,
                            category,
                            sub_category,
                        ),
                        lambda: fn(
                            search_query=keyword,
                            page=page,
                            main_tag=main_tag,
                            order_by=order_by,
                            time=time_filter,
                            category=category,
                            sub_category=sub_category,
                        ),
                    ]
                )

                for attempt in attempts:
                    try:
                        return attempt()
                    except NotImplementedError as exc:
                        detail = f"target={target_name}, method={name}"
                        if signature is not None:
                            detail += f", signature={signature}"
                        last_error = NotImplementedError(f"{detail}, error={repr(exc)}")
                        continue
                    except TypeError as exc:
                        detail = f"target={target_name}, method={name}"
                        if signature is not None:
                            detail += f", signature={signature}"
                        last_error = TypeError(f"{detail}, error={repr(exc)}")
                    except Exception as exc:
                        detail = f"target={target_name}, method={name}"
                        if signature is not None:
                            detail += f", signature={signature}"
                        last_error = RuntimeError(f"{detail}, error={repr(exc)}")
                        break

        if last_error is not None:
            raise last_error
        raise JMQueryError("未找到可用搜索方法")

    @staticmethod
    def _iter_search_targets(client, jmcomic=None) -> list[tuple[str, Any]]:
        targets: list[tuple[str, Any]] = [("client", client)]
        seen = {id(client)}

        for attr_name in (
            "client",
            "html_client",
            "api_client",
            "search_client",
            "album_client",
            "html",
            "api",
            "postman",
        ):
            try:
                target = getattr(client, attr_name, None)
            except Exception:
                continue
            if target is None or id(target) in seen:
                continue
            seen.add(id(target))
            targets.append((attr_name, target))

        if jmcomic is not None and id(jmcomic) not in seen:
            targets.append(("module", jmcomic))

        return targets

    @staticmethod
    def _build_search_attempt(
        fn,
        signature,
        keyword: str,
        page: int,
        main_tag: str,
        order_by: str,
        time_filter: str,
        category: str,
        sub_category: str,
    ):
        if signature is None:
            return None

        keyword_keys = ("search_query", "query", "keyword", "search_keyword", "text")
        mapping = {
            "page": page,
            "main_tag": main_tag,
            "order_by": order_by,
            "time": time_filter,
            "category": category,
            "sub_category": sub_category,
        }

        params = list(signature.parameters.values())
        kwargs = {}
        positional = []

        for param in params:
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            if param.name in keyword_keys:
                if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                    positional.append(keyword)
                else:
                    kwargs[param.name] = keyword
                continue

            if param.name in mapping:
                value = mapping[param.name]
                if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                    positional.append(value)
                else:
                    kwargs[param.name] = value

        if not positional and not kwargs:
            return None

        return lambda: fn(*positional, **kwargs)

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

        raise JMQueryError("未找到可用的 jmcomic 客户端实例")

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

        domain_bundle = bundle.get("domain") or {}
        proxy = bundle.get("proxy")
        account = bundle.get("account") or {}

        html_domain = domain_bundle.get("html") if isinstance(domain_bundle, dict) else None
        api_domain = domain_bundle.get("api") if isinstance(domain_bundle, dict) else None

        self._set_option_value(option, "proxies", proxy)
        self._set_option_value(option, "proxy", proxy)
        self._set_option_value(option, "domain", html_domain, containers=("client",))
        self._set_option_value(option, "postman", api_domain, containers=("client", "network", "plugins"))
        self._set_option_value(option, "api", api_domain, containers=("client", "network"))

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
        account_pool = self.config.get("account_pool") or []
        if account_pool:
            account = account_pool[0]

        html_domains = self.config.get("jm_domain_html") or []
        api_domains = self.config.get("jm_domain_api") or []
        proxies = self.config.get("proxy_pool") or []

        domain_bundle = None
        if html_domains or api_domains:
            domain_bundle = {
                "html": html_domains[0] if html_domains else None,
                "api": api_domains[0] if api_domains else None,
            }

        return {
            "account": account,
            "domain": domain_bundle,
            "proxy": proxies[0] if proxies else None,
        }

    def _max_attempts(self) -> int:
        if not self.pool_service:
            return 1

        accounts = max(1, len(self.pool_service.account_pool))
        html_domains = max(1, len(self.pool_service.domain_html_pool))
        api_domains = max(1, len(self.pool_service.domain_api_pool))
        proxies = max(1, len(self.pool_service.proxy_pool))
        return max(1, accounts * html_domains * api_domains * proxies)

    @staticmethod
    def _bundle_identity(bundle: dict[str, Any]) -> tuple:
        account = bundle.get("account") or {}
        domain_bundle = bundle.get("domain") or {}
        return (
            account.get("username"),
            account.get("password"),
            domain_bundle.get("html") if isinstance(domain_bundle, dict) else None,
            domain_bundle.get("api") if isinstance(domain_bundle, dict) else None,
            bundle.get("proxy"),
        )

    @staticmethod
    def _set_option_value(
        option: Any,
        key: str,
        value: Any,
        containers: tuple[str, ...] = ("client", "network", "plugins", "download"),
    ) -> None:
        if value in (None, "", {}):
            return

        if key != "domain":
            try:
                setattr(option, key, value)
                return
            except Exception:
                pass

        for container_name in containers:
            try:
                container = getattr(option, container_name, None)
            except Exception:
                continue
            if container is None:
                continue
            try:
                setattr(container, key, value)
                return
            except Exception:
                continue

        if key == "domain":
            try:
                setattr(option, key, value)
            except Exception:
                pass

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