from __future__ import annotations

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent


def read_plugin_config(plugin) -> dict:
    for attr in ("config", "plugin_config"):
        value = getattr(plugin, attr, None)
        if isinstance(value, dict):
            return value
    for attr in ("get_config", "load_config"):
        fn = getattr(plugin, attr, None)
        if callable(fn):
            try:
                value = fn()
                if isinstance(value, dict):
                    return value
            except Exception as exc:
                logger.warning("读取插件配置失败: %s", exc)
    return {}


async def handle_plugin_request(
    app,
    event: AstrMessageEvent | None = None,
    message: str = "",
    goal: str = "",
    album_id: str = "",
    chapter_id: str = "",
    **kwargs,
) -> str:
    actual_goal = (goal or message or kwargs.get("query") or kwargs.get("text") or "").strip()
    if not actual_goal:
        return "请描述你想执行的 JMComic 操作，例如：搜索本子、查看详情、读取评论、总结、推荐或下载。"

    if event is None:
        return f"已接收 JMComic 请求：{actual_goal}"

    return await app.workflow_service.run(
        event,
        actual_goal,
        album_id or None,
        chapter_id or None,
    )