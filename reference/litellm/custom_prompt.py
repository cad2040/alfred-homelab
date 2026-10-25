"""Optional Alfred persona prepend (sanitized teaching extract)."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

try:
    from litellm.integrations.custom_prompt_management import CustomPromptManagement
    from litellm.types.llms.openai import AllMessageValues
    from litellm.types.utils import StandardCallbackDynamicParams
except Exception:  # noqa: BLE001
    CustomPromptManagement = object  # type: ignore
    AllMessageValues = dict  # type: ignore
    StandardCallbackDynamicParams = dict  # type: ignore

ALFRED_SYSTEM_CONTENT = (
    "You are Alfred, a highly capable, polite, and strictly professional "
    "British butler and coding assistant. Always maintain this persona."
)
_SKIP = frozenset({"alfred-security", "alfred-technical-planner"})


def _prepend(messages: list) -> list:
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
        if call_type not in {"completion", "acompletion", "text_completion", "atext_completion"}:
            return data
        model = str(data.get("model") or "")
        if any(s in model for s in _SKIP):
            return data
        data["messages"] = _prepend(list(data.get("messages") or []))
        return data


prompt_management = AlfredCoderPromptManagement()
