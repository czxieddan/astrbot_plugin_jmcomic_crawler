from __future__ import annotations


class ToolExecutor:
    def __init__(self, app):
        self.app = app
        self.tool_map = {
            "jm_search_album": {"handler": self._search_album, "admin": False},
            "jm_get_album_detail": {"handler": self._get_album_detail, "admin": False},
            "jm_get_chapter_detail": {"handler": self._get_chapter_detail, "admin": False},
            "jm_create_album_download_task": {"handler": self._create_album_download_task, "admin": True},
            "jm_create_chapter_download_task": {"handler": self._create_chapter_download_task, "admin": True},
            "jm_create_batch_album_download_task": {"handler": self._create_batch_album_download_task, "admin": True},
            "jm_list_tasks": {"handler": self._list_tasks, "admin": False},
            "jm_get_task_status": {"handler": self._get_task_status, "admin": False},
            "jm_cancel_task": {"handler": self._cancel_task, "admin": True},
            "jm_get_album_comments": {"handler": self._get_album_comments, "admin": False},
            "jm_get_chapter_comments": {"handler": self._get_chapter_comments, "admin": False},
            "jm_summarize_album": {"handler": self._summarize_album, "admin": False},
            "jm_summarize_chapter": {"handler": self._summarize_chapter, "admin": False},
            "jm_recommend_similar_albums": {"handler": self._recommend_similar_albums, "admin": False},
            "jm_analyze_album_sentiment": {"handler": self._analyze_album_sentiment, "admin": False},
            "jm_run_workflow": {"handler": self._run_workflow, "admin": False},
        }

    async def execute(self, tool_name: str, event, *args, **kwargs) -> str:
        rule = self.tool_map[tool_name]
        if rule["admin"] and not self.app.permission_service.is_admin(event):
            return "当前仅管理员可执行该操作。"
        return await rule["handler"](event, *args, **kwargs)

    async def jm_search_album(self, event, keyword: str, page: int = 1) -> str:
        return await self.execute("jm_search_album", event, keyword, page)

    async def jm_get_album_detail(self, event, album_id: str) -> str:
        return await self.execute("jm_get_album_detail", event, album_id)

    async def jm_get_chapter_detail(self, event, chapter_id: str) -> str:
        return await self.execute("jm_get_chapter_detail", event, chapter_id)

    async def jm_create_album_download_task(self, event, album_id: str) -> str:
        return await self.execute("jm_create_album_download_task", event, album_id)

    async def jm_create_chapter_download_task(self, event, chapter_id: str) -> str:
        return await self.execute("jm_create_chapter_download_task", event, chapter_id)

    async def jm_create_batch_album_download_task(self, event, album_ids: str) -> str:
        return await self.execute("jm_create_batch_album_download_task", event, album_ids)

    async def jm_list_tasks(self, event) -> str:
        return await self.execute("jm_list_tasks", event)

    async def jm_get_task_status(self, event, task_id: str) -> str:
        return await self.execute("jm_get_task_status", event, task_id)

    async def jm_cancel_task(self, event, task_id: str) -> str:
        return await self.execute("jm_cancel_task", event, task_id)

    async def jm_get_album_comments(self, event, album_id: str, limit: int = 10) -> str:
        return await self.execute("jm_get_album_comments", event, album_id, limit)

    async def jm_get_chapter_comments(self, event, chapter_id: str, limit: int = 10) -> str:
        return await self.execute("jm_get_chapter_comments", event, chapter_id, limit)

    async def jm_summarize_album(self, event, album_id: str) -> str:
        return await self.execute("jm_summarize_album", event, album_id)

    async def jm_summarize_chapter(self, event, chapter_id: str) -> str:
        return await self.execute("jm_summarize_chapter", event, chapter_id)

    async def jm_recommend_similar_albums(self, event, album_id: str) -> str:
        return await self.execute("jm_recommend_similar_albums", event, album_id)

    async def jm_analyze_album_sentiment(self, event, album_id: str = "") -> str:
        return await self.execute("jm_analyze_album_sentiment", event, album_id)

    async def jm_run_workflow(self, event, goal: str, album_id: str = "", chapter_id: str = "") -> str:
        return await self.execute("jm_run_workflow", event, goal, album_id, chapter_id)

    async def _search_album(self, event, keyword: str, page: int = 1) -> str:
        return await self.app.action_handler.safe_call("搜索", self.app.action_handler.search(event, keyword, page))

    async def _get_album_detail(self, event, album_id: str) -> str:
        return await self.app.action_handler.safe_call("查询本子详情", self.app.action_handler.album_detail(event, album_id))

    async def _get_chapter_detail(self, event, chapter_id: str) -> str:
        return await self.app.action_handler.safe_call("查询章节详情", self.app.action_handler.chapter_detail(event, chapter_id))

    async def _create_album_download_task(self, event, album_id: str) -> str:
        return await self.app.action_handler.safe_call(
            "创建本子下载任务",
            self.app.action_handler.create_album_download_task(
                event,
                album_id,
                self.app.permission_service.get_sender_id(event),
                bool(self.app.config.get("download_zip_by_default", False)),
            ),
        )

    async def _create_chapter_download_task(self, event, chapter_id: str) -> str:
        return await self.app.action_handler.safe_call(
            "创建章节下载任务",
            self.app.action_handler.create_chapter_download_task(
                event,
                chapter_id,
                self.app.permission_service.get_sender_id(event),
                bool(self.app.config.get("download_zip_by_default", False)),
            ),
        )

    async def _create_batch_album_download_task(self, event, album_ids: str) -> str:
        ids = [item.strip() for item in album_ids.split(",") if item.strip()]
        return await self.app.action_handler.safe_call(
            "创建批量下载任务",
            self.app.action_handler.create_batch_album_download_task(
                event,
                ids,
                self.app.permission_service.get_sender_id(event),
                bool(self.app.config.get("download_zip_by_default", False)),
            ),
        )

    async def _list_tasks(self, event) -> str:
        return await self.app.action_handler.list_tasks(event)

    async def _get_task_status(self, event, task_id: str) -> str:
        return await self.app.action_handler.get_task_status(event, task_id)

    async def _cancel_task(self, event, task_id: str) -> str:
        return await self.app.action_handler.cancel_task(event, task_id)

    async def _get_album_comments(self, event, album_id: str, limit: int = 10) -> str:
        return await self.app.action_handler.safe_call("读取本子评论", self.app.action_handler.album_comments(event, album_id, limit))

    async def _get_chapter_comments(self, event, chapter_id: str, limit: int = 10) -> str:
        return await self.app.action_handler.safe_call("读取章节评论", self.app.action_handler.chapter_comments(event, chapter_id, limit))

    async def _summarize_album(self, event, album_id: str) -> str:
        return await self.app.action_handler.safe_call("总结本子", self.app.action_handler.summarize_album(event, album_id))

    async def _summarize_chapter(self, event, chapter_id: str) -> str:
        return await self.app.action_handler.safe_call("总结章节", self.app.action_handler.summarize_chapter(event, chapter_id))

    async def _recommend_similar_albums(self, event, album_id: str) -> str:
        return await self.app.action_handler.safe_call("推荐相似作品", self.app.action_handler.recommend(event, album_id))

    async def _analyze_album_sentiment(self, event, album_id: str = "") -> str:
        return await self.app.action_handler.safe_call(
            "评论情感分析",
            self.app.action_handler.analyze_album_sentiment(event, album_id or None),
        )

    async def _run_workflow(self, event, goal: str, album_id: str = "", chapter_id: str = "") -> str:
        return await self.app.action_handler.safe_call(
            "执行工作流",
            self.app.workflow_service.run(event, goal, album_id or None, chapter_id or None),
        )