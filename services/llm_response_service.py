from __future__ import annotations

import json
from typing import Any, Optional

from astrbot.api import logger


class LLMResponseService:
    def __init__(self, config: dict, context: Any):
        self.config = config or {}
        self.context = context

    async def polish(
        self,
        action: str,
        payload: dict[str, Any],
        fallback_text: str,
        event: Any | None = None,
    ) -> str:
        """
        将结构化结果交给当前 AstrBot 所使用的 LLM 进行人设化润色。
        如果运行时无法找到兼容的 AI 调用接口，则回退到 fallback_text。
        """
        if not self.config.get("llm_postprocess_enabled", True):
            return fallback_text

        prompt = self._build_prompt(action=action, payload=payload, fallback_text=fallback_text)
        response = await self._call_astrbot_llm(prompt=prompt, event=event)
        if response:
            return response
        return fallback_text

    def _build_prompt(self, action: str, payload: dict[str, Any], fallback_text: str) -> str:
        persona_prompt = self.config.get(
            "llm_persona_style_prompt",
            "请严格延续当前会话模型的人设、语气和表达风格。",
        )
        max_chars = int(self.config.get("llm_postprocess_max_chars", 4000) or 4000)

        payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
        if len(payload_json) > max_chars:
            payload_json = payload_json[: max_chars - 3] + "..."

        return "\n".join(
            [
                "你是 AstrBot 当前会话中的同一个助手，请不要改变当前人设。",
                persona_prompt,
                "",
                "任务：基于插件返回的结构化数据，生成一段适合聊天发送的自然语言回复。",
                "硬性要求：",
                "1. 不允许编造 payload 中不存在的事实。",
                "2. 不允许修改 ID、数量、状态、路径、标题等关键字段。",
                "3. 如果信息不足，明确说明“信息不足”或“当前只能给出有限结论”。",
                "4. 输出要自然，像同一位助手在聊天中回复用户。",
                "5. 可以优化措辞，但不要丢失关键事实。",
                "6. 若 payload 明确说明当前是骨架/占位/未真实下载，必须保留这一点。",
                "",
                f"当前动作: {action}",
                "结构化数据:",
                payload_json,
                "",
                "若你认为结构化数据过少，也至少基于以下原始文本进行润色，但仍不得编造：",
                fallback_text,
                "",
                "请直接输出最终回复，不要解释你的处理过程。",
            ]
        )

    async def _call_astrbot_llm(self, prompt: str, event: Any | None = None) -> Optional[str]:
        """
        兼容性调用：
        尝试多种可能的 AstrBot AI 接口。
        """
        candidates = [
            self._call_via_context_ai,
            self._call_via_provider_manager,
            self._call_via_conversation_api,
        ]

        for caller in candidates:
            try:
                result = await caller(prompt=prompt, event=event)
                if result:
                    return result.strip()
            except Exception as exc:  # pragma: no cover - 兼容不同运行时接口
                logger.warning("LLM 二次润色调用失败，尝试下一个接口: %s", exc)

        return None

    async def _call_via_context_ai(self, prompt: str, event: Any | None = None) -> Optional[str]:
        for attr in ("ai", "llm", "provider"):
            target = getattr(self.context, attr, None)
            if target is None:
                continue

            for method_name in ("ask", "chat", "complete", "generate", "text"):
                method = getattr(target, method_name, None)
                if not callable(method):
                    continue

                try:
                    result = method(prompt)
                    if hasattr(result, "__await__"):
                        result = await result
                    return self._extract_text(result)
                except TypeError:
                    if event is not None:
                        result = method(event, prompt)
                        if hasattr(result, "__await__"):
                            result = await result
                        return self._extract_text(result)

        return None

    async def _call_via_provider_manager(self, prompt: str, event: Any | None = None) -> Optional[str]:
        provider_manager = getattr(self.context, "provider_manager", None)
        if provider_manager is None:
            return None

        for method_name in ("text_chat", "chat", "ask", "complete"):
            method = getattr(provider_manager, method_name, None)
            if not callable(method):
                continue

            try:
                result = method(prompt)
                if hasattr(result, "__await__"):
                    result = await result
                return self._extract_text(result)
            except TypeError:
                if event is not None:
                    result = method(event, prompt)
                    if hasattr(result, "__await__"):
                        result = await result
                    return self._extract_text(result)

        return None

    async def _call_via_conversation_api(self, prompt: str, event: Any | None = None) -> Optional[str]:
        if event is None:
            return None

        possible_apis = [
            getattr(self.context, "conversation_manager", None),
            getattr(self.context, "text", None),
        ]
        for api in possible_apis:
            if api is None:
                continue
            for method_name in ("ask", "chat", "generate", "completion"):
                method = getattr(api, method_name, None)
                if not callable(method):
                    continue
                try:
                    result = method(event, prompt)
                    if hasattr(result, "__await__"):
                        result = await result
                    return self._extract_text(result)
                except Exception:
                    continue

        return None

    @staticmethod
    def _extract_text(result: Any) -> str:
        if result is None:
            return ""

        if isinstance(result, str):
            return result

        for attr in ("text", "content", "message", "result"):
            value = getattr(result, attr, None)
            if isinstance(value, str) and value.strip():
                return value

        if isinstance(result, dict):
            for key in ("text", "content", "message", "result"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        return str(result)