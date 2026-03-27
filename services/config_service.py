from __future__ import annotations

from copy import deepcopy
from typing import Any


class ConfigService:
    DEFAULTS = {
        "enabled": True,
        "cache_enabled": True,
        "cache_ttl_seconds": 300,
        "memory_enabled": True,
        "memory_ttl_seconds": 3600,
        "download_root_dir": "data/downloads",
        "download_zip_by_default": False,
        "max_concurrent_downloads": 2,
        "download_retry_count": 2,
        "download_timeout_seconds": 60,
        "admin_only_download": True,
        "admin_users": [],
        "comments_enabled": True,
        "summary_enabled": True,
        "sentiment_enabled": True,
        "recommend_enabled": True,
        "recommend_max_results": 5,
        "workflow_enabled": True,
        "dependency_check_on_startup": True,
        "auto_install_dependencies": True,
        "dependency_install_timeout_seconds": 300,
        "llm_postprocess_enabled": True,
        "llm_postprocess_max_chars": 4000,
        "llm_persona_style_prompt": "请严格延续当前会话模型的人设、语气和表达风格。",
        "jm_usernames": [],
        "jm_passwords": [],
        "jm_domains": [],
        "proxy_pool": [],
    }

    def __init__(self, raw_config: dict | None):
        self.raw_config = raw_config or {}
        self.config = self._normalize()

    def get_config(self) -> dict:
        return deepcopy(self.config)

    def _normalize(self) -> dict:
        merged = deepcopy(self.DEFAULTS)
        merged.update(self.raw_config)

        merged["admin_users"] = self._normalize_list(merged.get("admin_users"))
        merged["jm_usernames"] = self._normalize_list(merged.get("jm_usernames"))
        merged["jm_passwords"] = self._normalize_list(merged.get("jm_passwords"))
        merged["jm_domains"] = self._normalize_list(merged.get("jm_domains"))
        merged["proxy_pool"] = self._normalize_list(merged.get("proxy_pool"))

        self._validate_account_pool(merged["jm_usernames"], merged["jm_passwords"])
        merged["account_pool"] = [
            {"username": username, "password": password}
            for username, password in zip(merged["jm_usernames"], merged["jm_passwords"])
            if username and password
        ]

        return merged

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @staticmethod
    def _validate_account_pool(usernames: list[str], passwords: list[str]) -> None:
        if len(usernames) != len(passwords):
            raise ValueError("jm_usernames 与 jm_passwords 长度不一致，无法一一匹配")