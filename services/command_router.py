from __future__ import annotations

from services.jm_service import JMQueryError


class CommandRouter:
    def __init__(self, app):
        self.app = app
        self.command_map = {
            "搜索": {"handler": self._search, "need_arg": True, "admin": False},
            "search": {"handler": self._search, "need_arg": True, "admin": False},
            "本子": {"handler": self._album_detail, "need_arg": False, "admin": False},
            "album": {"handler": self._album_detail, "need_arg": False, "admin": False},
            "章节": {"handler": self._chapter_detail, "need_arg": False, "admin": False},
            "chapter": {"handler": self._chapter_detail, "need_arg": False, "admin": False},
            "下载本子": {"handler": self._download_album, "need_arg": False, "admin": True},
            "download_album": {"handler": self._download_album, "need_arg": False, "admin": True},
            "下载章节": {"handler": self._download_chapter, "need_arg": False, "admin": True},
            "download_chapter": {"handler": self._download_chapter, "need_arg": False, "admin": True},
            "批量下载本子": {"handler": self._batch_download_album, "need_arg": True, "admin": True},
            "batch_download_album": {"handler": self._batch_download_album, "need_arg": True, "admin": True},
            "任务列表": {"handler": self._list_tasks, "need_arg": False, "admin": False},
            "tasks": {"handler": self._list_tasks, "need_arg": False, "admin": False},
            "任务状态": {"handler": self._get_task_status, "need_arg": False, "admin": False},
            "task": {"handler": self._get_task_status, "need_arg": False, "admin": False},
            "取消任务": {"handler": self._cancel_task, "need_arg": False, "admin": True},
            "cancel_task": {"handler": self._cancel_task, "need_arg": False, "admin": True},
            "评论本子": {"handler": self._album_comments, "need_arg": False, "admin": False},
            "album_comments": {"handler": self._album_comments, "need_arg": False, "admin": False},
            "评论章节": {"handler": self._chapter_comments, "need_arg": False, "admin": False},
            "chapter_comments": {"handler": self._chapter_comments, "need_arg": False, "admin": False},
            "情感分析": {"handler": self._sentiment, "need_arg": False, "admin": False},
            "sentiment": {"handler": self._sentiment, "need_arg": False, "admin": False},
            "总结本子": {"handler": self._summary_album, "need_arg": False, "admin": False},
            "summary_album": {"handler": self._summary_album, "need_arg": False, "admin": False},
            "总结章节": {"handler": self._summary_chapter, "need_arg": False, "admin": False},
            "summary_chapter": {"handler": self._summary_chapter, "need_arg": False, "admin": False},
            "推荐": {"handler": self._recommend, "need_arg": False, "admin": False},
            "recommend": {"handler": self._recommend, "need_arg": False, "admin": False},
            "工作流": {"handler": self._workflow, "need_arg": True, "admin": False},
            "workflow": {"handler": self._workflow, "need_arg": True, "admin": False},
            "帮助": {"handler": self._help, "need_arg": False, "admin": False},
            "help": {"handler": self._help, "need_arg": False, "admin": False},
            "h": {"handler": self._help, "need_arg": False, "admin": False},
        }

    async def handle(self, event) -> str:
        message = (event.message_str or "").strip()
        parts = message.split()
        if len(parts) < 2:
            return self.app.response_builder.help_text()

        action = parts[1].strip()
        arg = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
        rule = self.command_map.get(action)
        if rule is None:
            return self.app.response_builder.help_text()

        if rule["admin"] and not self.app.permission_service.is_admin(event):
            return "当前仅管理员可执行该操作。"

        if rule["need_arg"] and not arg:
            return self._missing_arg_hint(action)

        return await rule["handler"](event, arg)

    async def _help(self, event, arg: str) -> str:
        return self.app.response_builder.help_text()

    async def _search(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("搜索", self.app.action_handler.search(event, arg, 1))

    async def _album_detail(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("查询本子详情", self.app.action_handler.album_detail(event, arg or None))

    async def _chapter_detail(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("查询章节详情", self.app.action_handler.chapter_detail(event, arg or None))

    async def _download_album(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call(
            "创建本子下载任务",
            self.app.action_handler.create_album_download_task(
                event,
                arg or None,
                self.app.permission_service.get_sender_id(event),
                bool(self.app.config.get("download_zip_by_default", False)),
            ),
        )

    async def _download_chapter(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call(
            "创建章节下载任务",
            self.app.action_handler.create_chapter_download_task(
                event,
                arg or None,
                self.app.permission_service.get_sender_id(event),
                bool(self.app.config.get("download_zip_by_default", False)),
            ),
        )

    async def _batch_download_album(self, event, arg: str) -> str:
        album_ids = [item.strip() for item in arg.split(",") if item.strip()]
        if not album_ids:
            raise JMQueryError("批量下载参数为空")
        return await self.app.action_handler.safe_call(
            "创建批量下载任务",
            self.app.action_handler.create_batch_album_download_task(
                event,
                album_ids,
                self.app.permission_service.get_sender_id(event),
                bool(self.app.config.get("download_zip_by_default", False)),
            ),
        )

    async def _list_tasks(self, event, arg: str) -> str:
        return await self.app.action_handler.list_tasks(event)

    async def _get_task_status(self, event, arg: str) -> str:
        return await self.app.action_handler.get_task_status(event, arg or None)

    async def _cancel_task(self, event, arg: str) -> str:
        return await self.app.action_handler.cancel_task(event, arg or None)

    async def _album_comments(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("读取本子评论", self.app.action_handler.album_comments(event, arg or None))

    async def _chapter_comments(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("读取章节评论", self.app.action_handler.chapter_comments(event, arg or None))

    async def _sentiment(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("评论情感分析", self.app.action_handler.analyze_album_sentiment(event, arg or None))

    async def _summary_album(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("总结本子", self.app.action_handler.summarize_album(event, arg or None))

    async def _summary_chapter(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("总结章节", self.app.action_handler.summarize_chapter(event, arg or None))

    async def _recommend(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("推荐相似作品", self.app.action_handler.recommend(event, arg or None))

    async def _workflow(self, event, arg: str) -> str:
        return await self.app.action_handler.safe_call("执行工作流", self.app.workflow_service.run(event, arg))

    @staticmethod
    def _missing_arg_hint(action: str) -> str:
        hints = {
            "搜索": "请提供搜索关键词，例如：/jm 搜索 人妻",
            "search": "请提供搜索关键词，例如：/jm 搜索 人妻",
            "批量下载本子": "请提供 id 列表，例如：/jm 批量下载本子 111,222,333",
            "batch_download_album": "请提供 id 列表，例如：/jm 批量下载本子 111,222,333",
            "工作流": "请提供工作流目标，例如：/jm 工作流 先看评论再总结",
            "workflow": "请提供工作流目标，例如：/jm 工作流 先看评论再总结",
        }
        return hints.get(action, "缺少必要参数。")