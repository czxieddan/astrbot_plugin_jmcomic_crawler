from __future__ import annotations


class WorkflowService:
    def __init__(self, action_handler, memory_service):
        self.action_handler = action_handler
        self.memory_service = memory_service

    async def run(self, event, goal: str, album_id: str | None = None, chapter_id: str | None = None) -> str:
        goal = (goal or "").strip()
        if not goal:
            return "未提供工作流目标，无法执行。"

        resolved_album = self.memory_service.resolve_album(event, album_id)
        resolved_chapter = self.memory_service.resolve_chapter(event, chapter_id)

        if "评论" in goal and "总结" in goal and resolved_album:
            comments = await self.action_handler.album_comments(event, resolved_album, 10)
            summary = await self.action_handler.summarize_album(event, resolved_album)
            return "\n\n".join(
                [
                    "已执行多步工作流：读取本子评论 -> 总结本子。",
                    comments,
                    summary,
                ]
            )

        if ("推荐" in goal or "相似" in goal) and resolved_album:
            summary = await self.action_handler.summarize_album(event, resolved_album)
            recommendation = await self.action_handler.recommend(event, resolved_album)
            return "\n\n".join(
                [
                    "已执行多步工作流：总结本子 -> 推荐相似作品。",
                    summary,
                    recommendation,
                ]
            )

        if ("下载" in goal or "保存" in goal) and resolved_album:
            task_text = await self.action_handler.create_album_download_task(
                event,
                resolved_album,
                self.memory_service.get_session_id(event),
                False,
            )
            return "\n\n".join(
                [
                    "已执行多步工作流：使用当前上下文中的本子创建下载任务。",
                    task_text,
                ]
            )

        if ("下载" in goal or "保存" in goal) and resolved_chapter:
            task_text = await self.action_handler.create_chapter_download_task(
                event,
                resolved_chapter,
                self.memory_service.get_session_id(event),
                False,
            )
            return "\n\n".join(
                [
                    "已执行多步工作流：使用当前上下文中的章节创建下载任务。",
                    task_text,
                ]
            )

        if resolved_album:
            detail = await self.action_handler.album_detail(event, resolved_album)
            return "\n\n".join(
                [
                    "已执行基础工作流：查询当前上下文中的本子详情。",
                    detail,
                ]
            )

        if resolved_chapter:
            detail = await self.action_handler.chapter_detail(event, resolved_chapter)
            return "\n\n".join(
                [
                    "已执行基础工作流：查询当前上下文中的章节详情。",
                    detail,
                ]
            )

        return "当前工作流未命中可执行路径，建议明确说明要搜索、评论、总结、推荐还是下载。"