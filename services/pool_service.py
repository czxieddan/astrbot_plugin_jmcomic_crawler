from __future__ import annotations

from typing import Any


class PoolService:
    def __init__(self, config: dict, state_manager):
        self.config = config or {}
        self.state_manager = state_manager
        self.state = self.state_manager.load()

        self.account_pool = self._build_account_pool()
        self.domain_html_pool = self._normalize_list(self.config.get("jm_domain_html"))
        self.domain_api_pool = self._normalize_list(self.config.get("jm_domain_api"))
        self.proxy_pool = self._normalize_list(self.config.get("proxy_pool"))

    def get_current_bundle(self) -> dict[str, Any]:
        return {
            "account": self._current_account(),
            "domain": self._current_domain_bundle(),
            "proxy": self._current_proxy(),
            "account_index": self._index("account_index", len(self.account_pool)),
            "domain_html_index": self._index("domain_html_index", len(self.domain_html_pool)),
            "domain_api_index": self._index("domain_api_index", len(self.domain_api_pool)),
            "proxy_index": self._index("proxy_index", len(self.proxy_pool)),
        }

    def mark_success(self) -> None:
        bundle = self.get_current_bundle()
        self.state_manager.update(last_success=bundle)

    def failover(self) -> dict[str, Any]:
        next_state = {
            "domain_html_index": self._next_index("domain_html_index", len(self.domain_html_pool)),
            "domain_api_index": self._next_index("domain_api_index", len(self.domain_api_pool)),
            "proxy_index": self._next_index("proxy_index", len(self.proxy_pool)),
            "account_index": self._next_index("account_index", len(self.account_pool)),
        }
        self.state.update(next_state)
        self.state_manager.save(self.state)
        return self.get_current_bundle()

    def validate(self) -> None:
        usernames = self.config.get("jm_usernames")
        passwords = self.config.get("jm_passwords")
        if usernames is None and passwords is None:
            return

        usernames = self._normalize_list(usernames)
        passwords = self._normalize_list(passwords)
        if len(usernames) != len(passwords):
            raise ValueError("jm_usernames 与 jm_passwords 长度不一致，无法一一匹配")

    def _build_account_pool(self) -> list[dict[str, str]]:
        self.validate()
        usernames = self._normalize_list(self.config.get("jm_usernames"))
        passwords = self._normalize_list(self.config.get("jm_passwords"))

        if not usernames and not passwords:
            return []

        if len(usernames) != len(passwords):
            raise ValueError("jm_usernames 与 jm_passwords 长度不一致，无法一一匹配")

        pool = []
        for username, password in zip(usernames, passwords):
            if username and password:
                pool.append({"username": username, "password": password})
        return pool

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _current_account(self) -> dict[str, str] | None:
        if not self.account_pool:
            return None
        return self.account_pool[self._index("account_index", len(self.account_pool))]

    def _current_domain_bundle(self) -> dict[str, str] | None:
        html = None
        api = None

        if self.domain_html_pool:
            html = self.domain_html_pool[self._index("domain_html_index", len(self.domain_html_pool))]
        if self.domain_api_pool:
            api = self.domain_api_pool[self._index("domain_api_index", len(self.domain_api_pool))]

        if not html and not api:
            return None
        return {"html": html, "api": api}

    def _current_proxy(self) -> str | None:
        if not self.proxy_pool:
            return None
        return self.proxy_pool[self._index("proxy_index", len(self.proxy_pool))]

    def _index(self, key: str, length: int) -> int:
        if length <= 0:
            return 0
        value = int(self.state.get(key, 0) or 0)
        return value % length

    def _next_index(self, key: str, length: int) -> int:
        if length <= 0:
            return 0
        current = self._index(key, length)
        return (current + 1) % length