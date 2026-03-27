from __future__ import annotations

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .services.plugin_application import PluginApplication
from .services.plugin_runtime import handle_plugin_request, read_plugin_config


@register(
    "astrbot_plugin_jmcomic_crawler",
    "CzXieDdan",
    "通过 LLM 自然语言调用查询 JMComic 元数据、评论、总结、推荐与下载任务，并支持配置池轮询、依赖自检、公共 API 对外复用。",
    "0.3.3",
)
class JMComicCrawlerPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config if isinstance(config, dict) else read_plugin_config(self)
        self.app = PluginApplication(self.config, context)

    def get_public_api(self):
        return self.app.public_api_service

    async def handler(
        self,
        event: AstrMessageEvent | None = None,
        message: str = "",
        goal: str = "",
        album_id: str = "",
        chapter_id: str = "",
        **kwargs,
    ) -> str:
        return await handle_plugin_request(
            self.app,
            event=event,
            message=message,
            goal=goal,
            album_id=album_id,
            chapter_id=chapter_id,
            **kwargs,
        )

    @filter.command("jm")
    async def jm_command(self, event: AstrMessageEvent):
        yield event.plain_result(await self.app.command_router.handle(event))

    @filter.llm_tool(name="jm_search_album")
    async def jm_search_album(self, event: AstrMessageEvent, keyword: str, page: int = 1) -> str:
        return await self.app.tool_executor.jm_search_album(event, keyword, page)

    @filter.llm_tool(name="jm_get_album_detail")
    async def jm_get_album_detail(self, event: AstrMessageEvent, album_id: str) -> str:
        return await self.app.tool_executor.jm_get_album_detail(event, album_id)

    @filter.llm_tool(name="jm_get_chapter_detail")
    async def jm_get_chapter_detail(self, event: AstrMessageEvent, chapter_id: str) -> str:
        return await self.app.tool_executor.jm_get_chapter_detail(event, chapter_id)

    @filter.llm_tool(name="jm_create_album_download_task")
    async def jm_create_album_download_task(self, event: AstrMessageEvent, album_id: str) -> str:
        return await self.app.tool_executor.jm_create_album_download_task(event, album_id)

    @filter.llm_tool(name="jm_create_chapter_download_task")
    async def jm_create_chapter_download_task(self, event: AstrMessageEvent, chapter_id: str) -> str:
        return await self.app.tool_executor.jm_create_chapter_download_task(event, chapter_id)

    @filter.llm_tool(name="jm_create_batch_album_download_task")
    async def jm_create_batch_album_download_task(self, event: AstrMessageEvent, album_ids: str) -> str:
        return await self.app.tool_executor.jm_create_batch_album_download_task(event, album_ids)

    @filter.llm_tool(name="jm_list_tasks")
    async def jm_list_tasks(self, event: AstrMessageEvent) -> str:
        return await self.app.tool_executor.jm_list_tasks(event)

    @filter.llm_tool(name="jm_get_task_status")
    async def jm_get_task_status(self, event: AstrMessageEvent, task_id: str) -> str:
        return await self.app.tool_executor.jm_get_task_status(event, task_id)

    @filter.llm_tool(name="jm_cancel_task")
    async def jm_cancel_task(self, event: AstrMessageEvent, task_id: str) -> str:
        return await self.app.tool_executor.jm_cancel_task(event, task_id)

    @filter.llm_tool(name="jm_get_album_comments")
    async def jm_get_album_comments(self, event: AstrMessageEvent, album_id: str, limit: int = 10) -> str:
        return await self.app.tool_executor.jm_get_album_comments(event, album_id, limit)

    @filter.llm_tool(name="jm_get_chapter_comments")
    async def jm_get_chapter_comments(self, event: AstrMessageEvent, chapter_id: str, limit: int = 10) -> str:
        return await self.app.tool_executor.jm_get_chapter_comments(event, chapter_id, limit)

    @filter.llm_tool(name="jm_summarize_album")
    async def jm_summarize_album(self, event: AstrMessageEvent, album_id: str) -> str:
        return await self.app.tool_executor.jm_summarize_album(event, album_id)

    @filter.llm_tool(name="jm_summarize_chapter")
    async def jm_summarize_chapter(self, event: AstrMessageEvent, chapter_id: str) -> str:
        return await self.app.tool_executor.jm_summarize_chapter(event, chapter_id)

    @filter.llm_tool(name="jm_recommend_similar_albums")
    async def jm_recommend_similar_albums(self, event: AstrMessageEvent, album_id: str) -> str:
        return await self.app.tool_executor.jm_recommend_similar_albums(event, album_id)

    @filter.llm_tool(name="jm_analyze_album_sentiment")
    async def jm_analyze_album_sentiment(self, event: AstrMessageEvent, album_id: str = "") -> str:
        return await self.app.tool_executor.jm_analyze_album_sentiment(event, album_id)

    @filter.llm_tool(name="jm_run_workflow")
    async def jm_run_workflow(
        self,
        event: AstrMessageEvent,
        goal: str,
        album_id: str = "",
        chapter_id: str = "",
    ) -> str:
        return await self.app.tool_executor.jm_run_workflow(event, goal, album_id, chapter_id)

    async def terminate(self):
        await self.app.close()