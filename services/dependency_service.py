from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path


class DependencyService:
    MODULE_NAME_MAP = {
        "jmcomic": "jmcomic",
        "httpx": "httpx",
    }

    def __init__(
        self,
        project_root: str,
        data_dir: str,
        auto_install: bool = True,
        check_on_startup: bool = True,
        timeout_seconds: int = 300,
    ):
        self.project_root = Path(project_root)
        self.data_dir = Path(data_dir)
        self.auto_install = auto_install
        self.check_on_startup = check_on_startup
        self.timeout_seconds = max(30, int(timeout_seconds or 300))
        self.state_path = self.data_dir / "config" / "dependency_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_dependencies(self) -> None:
        if not self.check_on_startup:
            return

        requirements = self._read_requirements()
        if not requirements:
            return

        req_hash = self._requirements_hash()
        state = self._load_state()

        missing = self._find_missing_modules(requirements)
        health_errors = self._verify_runtime_health()

        if (
            not missing
            and not health_errors
            and state.get("requirements_hash") == req_hash
            and state.get("last_result") == "success"
        ):
            return

        if (missing or health_errors) and self.auto_install:
            self._install_requirements()
            missing = self._find_missing_modules(requirements)
            health_errors = self._verify_runtime_health()

        result = "success" if not missing and not health_errors else "failed"
        self._save_state(
            {
                "requirements_hash": req_hash,
                "last_check_at": int(time.time()),
                "last_result": result,
                "missing_modules": missing,
                "health_errors": health_errors,
            }
        )

        if missing or health_errors:
            messages = []
            if missing:
                messages.append(f"缺少模块: {', '.join(missing)}")
            if health_errors:
                messages.append(f"运行时健康检查失败: {'; '.join(health_errors)}")
            raise RuntimeError("依赖检查失败，" + "；".join(messages))

    def _read_requirements(self) -> list[str]:
        path = self.project_root / "requirements.txt"
        if not path.exists():
            return []

        result = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            result.append(line)
        return result

    def _find_missing_modules(self, requirements: list[str]) -> list[str]:
        missing = []
        for requirement in requirements:
            package_name = self._package_name(requirement)
            module_name = self.MODULE_NAME_MAP.get(package_name, package_name.replace("-", "_"))
            try:
                importlib.import_module(module_name)
            except Exception:
                missing.append(module_name)
        return missing

    def _verify_runtime_health(self) -> list[str]:
        errors = []
        errors.extend(self._verify_jmcomic_runtime())
        errors.extend(self._verify_httpx_runtime())
        return errors

    def _verify_jmcomic_runtime(self) -> list[str]:
        try:
            jmcomic = importlib.import_module("jmcomic")
        except Exception as exc:
            return [f"jmcomic 无法导入: {exc}"]

        has_option = any(hasattr(jmcomic, name) for name in ("JmOption", "JMOption"))
        has_client_factory = any(
            hasattr(jmcomic, name)
            for name in ("create_client", "new_client", "JmcomicClient", "JMClient")
        )

        errors = []
        if not has_option:
            errors.append("jmcomic 缺少 JmOption/JMOption")
        if not has_client_factory:
            errors.append("jmcomic 缺少 client 工厂方法")
        return errors

    def _verify_httpx_runtime(self) -> list[str]:
        try:
            httpx = importlib.import_module("httpx")
        except Exception as exc:
            return [f"httpx 无法导入: {exc}"]

        try:
            timeout = httpx.Timeout(5)
            client = httpx.Client(timeout=timeout)
            client.close()
        except Exception as exc:
            return [f"httpx 运行时初始化失败: {exc}"]

        return []

    def _install_requirements(self) -> None:
        path = self.project_root / "requirements.txt"
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(path)],
            cwd=str(self.project_root),
            check=True,
            timeout=self.timeout_seconds,
        )

    def _requirements_hash(self) -> str:
        path = self.project_root / "requirements.txt"
        if not path.exists():
            return ""
        content = path.read_text(encoding="utf-8")
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _package_name(requirement: str) -> str:
        for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
            if sep in requirement:
                return requirement.split(sep, 1)[0].strip()
        return requirement.strip()

    def _load_state(self) -> dict:
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_state(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")