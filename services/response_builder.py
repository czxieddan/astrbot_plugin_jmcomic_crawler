from __future__ import annotations

from typing import Any

from ..models.comment import CommentResult
from ..models.dto import AlbumDetail, ChapterDetail, SearchResult


class ResponseBuilder:
    def search_payload(self, result: SearchResult) -> dict[str, Any]:
        return {
            "type": "search_result",
            "keyword": result.keyword,
            "page": result.page,
            "count": len(result.items),
            "items": [
                {
                    "album_id": item.album_id,
                    "name": item.name,
                    "author": item.author,
                    "tags": item.tags,
                }
                for item in result.items
            ],
        }

    def album_payload(self, detail: AlbumDetail) -> dict[str, Any]:
        return {
            "type": "album_detail",
            "album_id": detail.album_id,
            "name": detail.name,
            "author": detail.author,
            "tags": detail.tags,
            "description": detail.description,
            "likes": detail.likes,
            "page_count": detail.page_count,
            "chapter_count": len(detail.chapters),
            "chapters": [
                {"chapter_id": chapter.chapter_id, "name": chapter.name}
                for chapter in detail.chapters
            ],
        }

    def chapter_payload(self, detail: ChapterDetail) -> dict[str, Any]:
        return {
            "type": "chapter_detail",
            "chapter_id": detail.chapter_id,
            "name": detail.name,
            "album_id": detail.album_id,
            "album_name": detail.album_name,
            "image_count": detail.image_count,
            "publish_time": detail.publish_time,
        }

    def comments_payload(self, comments: CommentResult) -> dict[str, Any]:
        return {
            "type": "comments",
            "target_id": comments.target_id,
            "target_type": comments.target_type,
            "count": len(comments.items),
            "items": [
                {
                    "comment_id": item.comment_id,
                    "user_name": item.user_name,
                    "content": item.content,
                    "created_at": item.created_at,
                    "likes": item.likes,
                    "reply_count": item.reply_count,
                }
                for item in comments.items
            ],
        }

    def task_payload(self, task: dict) -> dict[str, Any]:
        return {
            "type": "task",
            "task_id": task.get("task_id"),
            "task_type": task.get("task_type"),
            "status": task.get("status"),
            "target": task.get("target_id") or task.get("target_ids"),
            "progress": task.get("progress"),
            "completed_items": task.get("completed_items"),
            "total_items": task.get("total_items"),
            "save_path": task.get("save_path"),
            "zip_path": task.get("zip_path"),
            "error_message": task.get("error_message"),
        }

    def task_list_payload(self, tasks: list[dict]) -> dict[str, Any]:
        return {
            "type": "task_list",
            "count": len(tasks),
            "items": [self.task_payload(task) for task in tasks],
        }

    def render_search_result(self, result: SearchResult) -> str:
        if not result.items:
            return "未找到匹配的 JMComic 本子。"

        lines = [
            f"JM 搜索结果：关键词「{result.keyword}」，第 {result.page} 页，共返回 {len(result.items)} 条"
        ]
        for index, item in enumerate(result.items, start=1):
            tags = " / ".join(item.tags[:5]) if item.tags else "无"
            lines.append(
                "\n".join(
                    [
                        f"{index}. {item.name}",
                        f"   album_id: {item.album_id}",
                        f"   作者: {item.author or '未知'}",
                        f"   标签: {tags}",
                    ]
                )
            )
        return "\n".join(lines)

    def render_album_detail(self, detail: AlbumDetail) -> str:
        lines = [
            "JM 本子详情",
            f"- album_id: {detail.album_id}",
            f"- 标题: {detail.name}",
            f"- 作者: {detail.author or '未知'}",
            f"- 标签: {' / '.join(detail.tags) if detail.tags else '无'}",
            f"- 章节数: {len(detail.chapters)}",
            f"- 页数: {detail.page_count or '未知'}",
            f"- 喜欢: {detail.likes or '未知'}",
            f"- 简介: {detail.description or '无'}",
        ]
        if detail.chapters:
            lines.append("")
            lines.append("章节列表")
            for idx, chapter in enumerate(detail.chapters, start=1):
                lines.append(f"{idx}. {chapter.name} (chapter_id: {chapter.chapter_id})")
        return "\n".join(lines)

    def render_chapter_detail(self, detail: ChapterDetail) -> str:
        return "\n".join(
            [
                "JM 章节详情",
                f"- chapter_id: {detail.chapter_id}",
                f"- 标题: {detail.name}",
                f"- 所属本子: {detail.album_name or '未知'}",
                f"- album_id: {detail.album_id or '未知'}",
                f"- 图片数量: {detail.image_count if detail.image_count is not None else '未知'}",
                f"- 发布时间: {detail.publish_time or '未知'}",
            ]
        )

    def render_comments(self, comments: CommentResult) -> str:
        lines = [f"JM 评论列表（{comments.target_type}:{comments.target_id}）"]
        if not comments.items:
            lines.append("暂无评论数据。")
            return "\n".join(lines)

        for idx, item in enumerate(comments.items, start=1):
            lines.append(
                "\n".join(
                    [
                        f"{idx}. {item.user_name}",
                        f"   内容: {item.content}",
                        f"   时间: {item.created_at or '未知'}",
                        f"   点赞: {item.likes if item.likes is not None else '未知'}",
                    ]
                )
            )
        return "\n".join(lines)

    def render_task(self, task: dict) -> str:
        return "\n".join(
            [
                "JM 下载任务",
                f"- task_id: {task.get('task_id')}",
                f"- 类型: {task.get('task_type')}",
                f"- 状态: {task.get('status')}",
                f"- 目标: {task.get('target_id') or task.get('target_ids')}",
                f"- 进度: {task.get('progress', 0)}",
                f"- 已完成: {task.get('completed_items', 0)} / {task.get('total_items', 0)}",
                f"- 保存路径: {task.get('save_path') or '未生成'}",
                f"- 压缩包: {task.get('zip_path') or '未生成'}",
                f"- 错误: {task.get('error_message') or '无'}",
            ]
        )

    def render_task_list(self, tasks: list[dict]) -> str:
        if not tasks:
            return "暂无下载任务。"

        lines = ["JM 下载任务列表"]
        for task in tasks:
            lines.append(
                f"- {task.get('task_id')} | {task.get('task_type')} | {task.get('status')} | {task.get('target_id') or task.get('target_ids')}"
            )
        return "\n".join(lines)

    def help_text(self) -> str:
        return "\n".join(
            [
                "JMComic 插件用法：",
                "/jm 搜索 <关键词>",
                "/jm 本子 <album_id>",
                "/jm 章节 <chapter_id>",
                "/jm 下载本子 <album_id>",
                "/jm 下载章节 <chapter_id>",
                "/jm 批量下载本子 <id1,id2,id3>",
                "/jm 任务列表",
                "/jm 任务状态 <task_id>",
                "/jm 取消任务 <task_id>",
                "/jm 评论本子 <album_id>",
                "/jm 评论章节 <chapter_id>",
                "/jm 总结本子 <album_id>",
                "/jm 总结章节 <chapter_id>",
                "/jm 推荐 <album_id>",
                "/jm 帮助",
            ]
        )