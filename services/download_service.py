from __future__ import annotations

import asyncio
import zipfile
from pathlib import Path
from typing import Any, Optional

import httpx

from managers.scheduler_manager import SchedulerManager
from managers.task_manager import TaskManager
from services.jm_service import JMComicService, JMQueryError


class DownloadService:
    def __init__(
        self,
        config: dict,
        jm_service: JMComicService,
        task_manager: TaskManager,
        scheduler_manager: SchedulerManager | None = None,
    ):
        self.config = config or {}
        self.jm_service = jm_service
        self.task_manager = task_manager
        self.scheduler_manager = scheduler_manager or SchedulerManager()
        self.retry_count = max(1, int(self.config.get("download_retry_count", 2) or 2))
        self.timeout_seconds = max(10, int(self.config.get("download_timeout_seconds", 60) or 60))
        self.proxies = self.config.get("proxies") or None

        base_dir = Path(self.config.get("download_root_dir") or "data/downloads")
        self.download_root_dir = base_dir
        self.download_root_dir.mkdir(parents=True, exist_ok=True)

    async def create_album_download_task(
        self,
        album_id: str,
        requested_by: Optional[str] = None,
        create_zip: bool = False,
    ) -> dict:
        task = self.task_manager.create_download_task(
            task_type="album_download",
            target_id=album_id,
            requested_by=requested_by,
            extra={"create_zip": create_zip},
        )
        self.scheduler_manager.create_background_task(
            task.task_id,
            lambda: self._run_album_download(task.task_id, album_id, create_zip=create_zip),
        )
        return task.to_dict()

    async def create_chapter_download_task(
        self,
        chapter_id: str,
        requested_by: Optional[str] = None,
        create_zip: bool = False,
    ) -> dict:
        task = self.task_manager.create_download_task(
            task_type="chapter_download",
            target_id=chapter_id,
            requested_by=requested_by,
            extra={"create_zip": create_zip},
        )
        self.scheduler_manager.create_background_task(
            task.task_id,
            lambda: self._run_chapter_download(task.task_id, chapter_id, create_zip=create_zip),
        )
        return task.to_dict()

    async def create_batch_album_download_task(
        self,
        album_ids: list[str],
        requested_by: Optional[str] = None,
        create_zip: bool = False,
    ) -> dict:
        task = self.task_manager.create_batch_task(
            task_type="batch_album_download",
            target_ids=album_ids,
            requested_by=requested_by,
        )

        for album_id in album_ids:
            child = await self.create_album_download_task(
                album_id=album_id,
                requested_by=requested_by,
                create_zip=create_zip,
            )
            task.child_task_ids.append(child["task_id"])

        task.status = "running"
        task.completed_items = 0
        self.task_manager.save_batch_task(task)
        return task.to_dict()

    async def _run_album_download(self, task_id: str, album_id: str, create_zip: bool = False) -> None:
        self.task_manager.update_task_status(task_id, status="running", progress=0.01)
        try:
            detail = await self.jm_service.get_album_detail(album_id)
            album_dir = self.download_root_dir / f"album_{album_id}"
            album_dir.mkdir(parents=True, exist_ok=True)

            chapters = detail.chapters or []
            total = max(len(chapters), 1)
            self.task_manager.update_task_status(task_id, status="running", total_items=total)

            if not chapters:
                placeholder = album_dir / "README.txt"
                placeholder.write_text(
                    "\n".join(
                        [
                            f"album_id={album_id}",
                            f"title={detail.name}",
                            "当前未解析到章节列表，已保留目录。",
                        ]
                    ),
                    encoding="utf-8",
                )
                self.task_manager.update_task_status(
                    task_id,
                    status="running",
                    completed_items=1,
                    total_items=1,
                    progress=1.0,
                    save_path=str(album_dir),
                )
            else:
                for idx, chapter in enumerate(chapters, start=1):
                    if self.scheduler_manager.is_cancelled(task_id):
                        self.task_manager.update_task_status(task_id, status="cancelled")
                        return

                    chapter_dir = album_dir / f"chapter_{chapter.chapter_id}"
                    chapter_dir.mkdir(parents=True, exist_ok=True)

                    urls = await asyncio.to_thread(self._extract_image_urls_for_chapter, chapter.chapter_id)
                    if urls:
                        await self._download_images(task_id, urls, chapter_dir)
                    else:
                        placeholder = chapter_dir / "README.txt"
                        placeholder.write_text(
                            "\n".join(
                                [
                                    f"album_id={album_id}",
                                    f"chapter_id={chapter.chapter_id}",
                                    f"title={chapter.name}",
                                    "当前未能从运行时接口中解析出图片 URL，已保留占位目录。",
                                ]
                            ),
                            encoding="utf-8",
                        )

                    self.task_manager.update_task_status(
                        task_id,
                        status="running",
                        completed_items=idx,
                        progress=idx / total,
                        save_path=str(album_dir),
                    )

            zip_path = self._zip_directory(album_dir) if create_zip else None
            self.task_manager.update_task_status(
                task_id,
                status="completed",
                progress=1.0,
                save_path=str(album_dir),
                zip_path=str(zip_path) if zip_path else None,
            )
        except asyncio.CancelledError:
            self.task_manager.update_task_status(task_id, status="cancelled")
            raise
        except JMQueryError as exc:
            self.task_manager.update_task_status(task_id, status="failed", error_message=str(exc))
        except Exception as exc:
            self.task_manager.update_task_status(task_id, status="failed", error_message=str(exc))

    async def _run_chapter_download(
        self,
        task_id: str,
        chapter_id: str,
        create_zip: bool = False,
    ) -> None:
        self.task_manager.update_task_status(task_id, status="running", progress=0.01)
        try:
            detail = await self.jm_service.get_chapter_detail(chapter_id)
            chapter_dir = self.download_root_dir / f"chapter_{chapter_id}"
            chapter_dir.mkdir(parents=True, exist_ok=True)

            urls = await asyncio.to_thread(self._extract_image_urls_for_chapter, chapter_id)
            if urls:
                self.task_manager.update_task_status(task_id, status="running", total_items=len(urls))
                await self._download_images(task_id, urls, chapter_dir)
            else:
                placeholder = chapter_dir / "README.txt"
                placeholder.write_text(
                    "\n".join(
                        [
                            f"chapter_id={chapter_id}",
                            f"title={detail.name}",
                            f"album_id={detail.album_id or ''}",
                            "当前未能从运行时接口中解析出图片 URL，已保留占位目录。",
                        ]
                    ),
                    encoding="utf-8",
                )
                self.task_manager.update_task_status(
                    task_id,
                    status="running",
                    total_items=1,
                    completed_items=1,
                    progress=1.0,
                    save_path=str(chapter_dir),
                )

            zip_path = self._zip_directory(chapter_dir) if create_zip else None
            self.task_manager.update_task_status(
                task_id,
                status="completed",
                progress=1.0,
                save_path=str(chapter_dir),
                zip_path=str(zip_path) if zip_path else None,
            )
        except asyncio.CancelledError:
            self.task_manager.update_task_status(task_id, status="cancelled")
            raise
        except JMQueryError as exc:
            self.task_manager.update_task_status(task_id, status="failed", error_message=str(exc))
        except Exception as exc:
            self.task_manager.update_task_status(task_id, status="failed", error_message=str(exc))

    async def _download_images(self, task_id: str, urls: list[str], target_dir: Path) -> None:
        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, proxy=self.proxies, follow_redirects=True) as client:
            total = len(urls)
            completed = 0
            for index, url in enumerate(urls, start=1):
                if self.scheduler_manager.is_cancelled(task_id):
                    self.task_manager.update_task_status(task_id, status="cancelled")
                    return

                suffix = Path(url.split("?")[0]).suffix or ".jpg"
                file_path = target_dir / f"{index:04d}{suffix}"
                ok = await self._download_with_retry(client, url, file_path)
                if ok:
                    completed += 1

                progress = completed / total if total else 1.0
                self.task_manager.update_task_status(
                    task_id,
                    status="running",
                    completed_items=completed,
                    total_items=total,
                    progress=progress,
                    save_path=str(target_dir),
                )

            if completed == 0 and total > 0:
                raise JMQueryError("图片 URL 已解析，但全部下载失败")

    async def _download_with_retry(self, client: httpx.AsyncClient, url: str, file_path: Path) -> bool:
        for _ in range(self.retry_count):
            try:
                response = await client.get(url)
                response.raise_for_status()
                file_path.write_bytes(response.content)
                return True
            except Exception:
                await asyncio.sleep(0.5)
        return False

    def _extract_image_urls_for_chapter(self, chapter_id: str) -> list[str]:
        client = self.jm_service._init_client()
        method_names = (
            "get_photo_detail",
            "get_chapter_detail",
            "chapter_detail",
            "get_chapter",
            "fetch_photo_detail",
        )
        raw = None
        for name in method_names:
            method = getattr(client, name, None)
            if not callable(method):
                continue
            try:
                raw = method(chapter_id)
                break
            except Exception:
                continue

        if raw is None:
            return []

        candidates = self._pick(raw, ("images", "page_arr", "image_list", "data_original_domain"))
        if isinstance(candidates, list):
            return [str(item) for item in candidates if str(item).startswith("http")]

        if isinstance(raw, dict):
            for key in ("images", "page_arr", "image_list"):
                value = raw.get(key)
                if isinstance(value, list):
                    return [str(item) for item in value if str(item).startswith("http")]

        for attr in ("images", "page_arr", "image_list"):
            value = getattr(raw, attr, None)
            if isinstance(value, list):
                return [str(item) for item in value if str(item).startswith("http")]

        return []

    @staticmethod
    def _pick(obj: Any, keys: tuple[str, ...]) -> Any:
        for key in keys:
            if isinstance(obj, dict) and key in obj:
                return obj[key]
            if hasattr(obj, key):
                return getattr(obj, key)
        return None

    def _zip_directory(self, directory: Path) -> Path:
        zip_path = directory.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in directory.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=path.relative_to(directory))
        return zip_path