"""Optional persona prepend (template — off by default).

Set ``ALFRED_PERSONA`` to a non-empty string to enable, or leave unset/empty
to skip. Remove ``custom_prompt.prompt_management`` from config callbacks to
disable entirely.
"""
from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple

try:
    from litellm.integrations.custom_prompt_management import CustomPromptManagement
    from litellm.types.llms.openai import AllMessageValues
    from litellm.types.utils import StandardCallbackDynamicParams
except Exception:  # noqa: BLE001
    CustomPromptManagement = object  # type: ignore
    AllMessageValues = dict  # type: ignore
    StandardCallbackDynamicParams = dict  # type: ignore

# Empty by default — template stays clinical unless the operator opts in.
ALFRED_SYSTEM_CONTENT = os.environ.get("ALFRED_PERSONA", "")
_SKIP = frozenset(
    s.strip()
    for s in os.environ.get(
        "ALFRED_PERSONA_SKIP", "alfred-security,alfred-technical-planner"
    ).split(",")
    if s.strip()
)


def _prepend(messages: list) -> list:
    if not (ALFRED_SYSTEM_CONTENT or "").strip():
        return messages
    for msg in messages or []:
        if isinstance(msg, dict) and msg.get("role") == "system":
            if ALFRED_SYSTEM_CONTENT in str(msg.get("content") or ""):
                return messages
    return [{"role": "system", "content": ALFRED_SYSTEM_CONTENT}, *(messages or [])]


class AlfredCoderPromptManagement(CustomPromptManagement):
    def get_chat_completion_prompt(
        self,
        model: str,
        messages: List[AllMessageValues],
        non_default_params: dict,
        prompt_id: Optional[str],
        prompt_variables: Optional[dict],
        dynamic_callback_params: StandardCallbackDynamicParams,
        prompt_label: Optional[str] = None,
        prompt_version: Optional[int] = None,
    ) -> Tuple[str, List[AllMessageValues], dict]:
        if not any(s in str(model) for s in _SKIP):
            messages = _prepend(list(messages or []))  # type: ignore[assignment]
        return model, messages, non_default_params

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> Any:
        if call_type not in {
            "completion",
            "acompletion",
            "text_completion",
            "atext_completion",
        }:
            return data
        model = str(data.get("model") or "")
        if any(s in model for s in _SKIP):
            return data
        data["messages"] = _prepend(list(data.get("messages") or []))
        return data


prompt_management = AlfredCoderPromptManagement()
