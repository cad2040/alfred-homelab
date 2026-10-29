"""Sentinel runtime: logging, HTTP, VRAM lock, LiteLLM chat with retries."""
from __future__ import annotations

import fcntl
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from alfred_memory_rubric import RUBRIC_RESPONSE_FORMAT
from alfred_domain_tagger import DOMAIN_TAG_RESPONSE_FORMAT
from alfred_sentinel_prompts import chat_content_looks_broken
from alfred_sentinel_config import (
    CODER_TAG,
    LITELLM,
    LITELLM_BACKOFF_S,
    LITELLM_RETRIES,
    LOCK_PATH,
    OLLAMA,
    REASONER_TAG,
    RETRYABLE_MARKERS,
    SECURITY_TAG,
)

try:
    from alfred_vram import (  # noqa: E402
        FIM_TAG as _FIM_TAG,
        SLOT2_CHAT_MODELS,
        flush_slot2_chat as _vram_flush,
        prepare_specialist_hot_swap as _vram_prepare,
        unload_fim as _vram_unload_fim,
        warm_fim_for_bronze as _vram_warm_fim,
    )
except Exception:  # noqa: BLE001
    SLOT2_CHAT_MODELS = (
        REASONER_TAG,
        CODER_TAG,
        "qwen2.5-coder:14b-instruct-q3_K_M",
        "qwen2.5-coder:7b-instruct-q5_K_M",
        SECURITY_TAG,
        "qwen3.5:9b",
    )
    _vram_flush = None
    _vram_prepare = None
    _vram_unload_fim = None
    _vram_warm_fim = None
    _FIM_TAG = "qwen2.5-coder:1.5b-base"


def log(msg: str) -> None:
    print(msg, flush=True)


def _is_retryable_llm_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, urllib.error.URLError, ConnectionError)):
        return True
    text = str(exc)
    return any(marker in text for marker in RETRYABLE_MARKERS)


def load_master_key() -> str:
    key = os.environ.get("LITELLM_MASTER_KEY", "").strip()
    if key:
        return key
    env_file = Path(os.environ.get("ALFRED_ENV_FILE", "")).expanduser()
    if not env_file.is_file():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("LITELLM_MASTER_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def http_json(
    method: str,
    url: str,
    body: dict | None = None,
    headers: dict | None = None,
    timeout: int = 300,
):
    data = None if body is None else json.dumps(body).encode()
    hdrs = dict(headers or {})
    if body is not None:
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def acquire_lock(timeout_s: int = 600):
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fh = open(LOCK_PATH, "a+", encoding="utf-8")
    deadline = time.time() + timeout_s
    while True:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fh.seek(0)
            fh.truncate()
            fh.write(f"alfred-sentinel pid={os.getpid()} ts={int(time.time())}\n")
            fh.flush()
            return fh
        except BlockingIOError:
            if time.time() >= deadline:
                fh.close()
                raise RuntimeError(f"could not acquire {LOCK_PATH}")
            time.sleep(2)


def flush_models(*models: str) -> None:
    if _vram_flush is not None and (not models or set(models) <= set(SLOT2_CHAT_MODELS)):
        try:
            _vram_flush(*models, quiet=False)
            return
        except Exception as exc:  # noqa: BLE001
            log(f"warn: alfred_vram flush failed: {exc}")
    for model in models or SLOT2_CHAT_MODELS:
        try:
            http_json(
                "POST",
                f"{OLLAMA}/api/generate",
                {"model": model, "keep_alive": 0, "prompt": ""},
                timeout=60,
            )
        except Exception as exc:  # noqa: BLE001
            log(f"warn: flush {model}: {exc}")


def prepare_specialist(incoming: str) -> None:
    """Single-resident: flush FIM + other chat tags before ``incoming`` owns VRAM."""
    tag = (incoming or "").strip()
    if not tag:
        return
    if _vram_prepare is not None:
        try:
            _vram_prepare(tag, quiet=False)
            log(f"vram: prepared single-resident for {tag}")
            return
        except Exception as exc:  # noqa: BLE001
            log(f"warn: alfred_vram prepare failed: {exc}")
    if _vram_unload_fim is not None:
        try:
            _vram_unload_fim(quiet=False)
        except Exception as exc:  # noqa: BLE001
            log(f"warn: unload FIM: {exc}")
    flush_models()


def pin_fim_model() -> None:
    """Warm FIM briefly for Bronze summarize (not a permanent pin)."""
    if _vram_warm_fim is not None:
        try:
            _vram_warm_fim(quiet=False)
            return
        except Exception as exc:  # noqa: BLE001
            log(f"warn: alfred_vram warm FIM failed: {exc}")
    try:
        http_json(
            "POST",
            f"{OLLAMA}/api/generate",
            {"model": _FIM_TAG, "keep_alive": "2m", "prompt": ""},
            timeout=120,
        )
        log(f"warmed {_FIM_TAG} keep_alive=2m")
    except Exception as exc:  # noqa: BLE001
        log(f"warn: warm FIM {_FIM_TAG}: {exc}")


def litellm_chat_safe(
    master_key: str,
    model: str,
    user: str,
    system: str | None = None,
    *,
    fallback_model: str | None = "alfred-reasoner",
    retries: int | None = None,
    backoff_s: float | None = None,
    prepare: bool = True,
) -> str:
    """Chat completion with backoff retries + soft fallback on ChatML junk."""
    attempts = LITELLM_RETRIES if retries is None else max(1, int(retries))
    base_backoff = LITELLM_BACKOFF_S if backoff_s is None else max(0.0, float(backoff_s))

    def _once(use_model: str) -> str:
        payload = {
            "model": use_model,
            "messages": ([{"role": "system", "content": system}] if system else [])
            + [{"role": "user", "content": user}],
            "temperature": 0.2,
            "max_tokens": 1200,
        }
        if system and (
            "Score ONE" in system
            or "ONLY valid JSON" in system
            or "domain registrar" in system
        ):
            payload["response_format"] = (
                DOMAIN_TAG_RESPONSE_FORMAT
                if "domain registrar" in system
                else RUBRIC_RESPONSE_FORMAT
            )
        try:
            data = http_json(
                "POST",
                f"{LITELLM}/chat/completions",
                payload,
                headers={"Authorization": f"Bearer {master_key}"},
                timeout=420,
            )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            raise RuntimeError(f"HTTP {exc.code} from {use_model}: {detail}") from exc
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        return (msg.get("content") or msg.get("reasoning_content") or "").strip()

    def _with_retries(use_model: str) -> str:
        last_exc: BaseException | None = None
        for attempt in range(1, attempts + 1):
            try:
                if prepare:
                    prepare_specialist(use_model)
                return _once(use_model)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= attempts or not _is_retryable_llm_error(exc):
                    raise
                delay = base_backoff * (2 ** (attempt - 1))
                log(
                    f"warn: {use_model} attempt {attempt}/{attempts} failed: {exc}; "
                    f"backoff {delay:.0f}s then re-prepare"
                )
                try:
                    flush_models()
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(delay)
        assert last_exc is not None
        raise last_exc

    text = _with_retries(model)
    if not chat_content_looks_broken(text):
        return text
    if fallback_model and fallback_model != model:
        print(
            f"warn: {model} returned template/empty junk; retrying via {fallback_model}",
            file=sys.stderr,
        )
        text2 = _with_retries(fallback_model)
        if not chat_content_looks_broken(text2):
            return text2
    raise RuntimeError(
        f"{model} produced unusable ChatML/empty output"
        + (f" (fallback {fallback_model} also failed)" if fallback_model else "")
    )
