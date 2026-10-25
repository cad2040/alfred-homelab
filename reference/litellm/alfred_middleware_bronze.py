"""Teaching Bronze middleware for LiteLLM (sanitized public extract).

Compresses long chats before specialist ``num_ctx`` overflow:

1. Read per-alias budgets from ``bronze_budgets.yaml`` (else derive ≈0.61×num_ctx)
2. If tokens (messages + tools) exceed threshold → summarize the middle
3. Prefer a small base FIM tag via Ollama ``/api/generate`` (never ``/api/chat`` on base)
4. Optional Chroma upsert is best-effort and never blocks the chat
5. On summarize failure → extractive stub so the request still fits

Wire-up: see ``docs/guides/wire-middleware.md``.
Register as ``alfred_middleware_bronze.proxy_handler_instance`` in config.yaml.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from litellm.integrations.custom_logger import CustomLogger
except Exception:  # noqa: BLE001
    from litellm.proxy.hooks.callback import CustomLogger  # type: ignore

log = logging.getLogger("alfred.middleware.bronze")

OLLAMA = os.environ.get("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
CHROMA = os.environ.get("CHROMA_URL", "").rstrip("/")  # empty = skip ingest
FIM_TAG = os.environ.get("ALFRED_FIM_TAG", "qwen2.5-coder:1.5b-base")
FIM_ALIAS = "alfred-fim"
EMBED_MODEL = os.environ.get("ALFRED_EMBED_TAG", "nomic-embed-text")
BRONZE_COLLECTION = "bronze_context_log"
PRESERVE_TAIL = int(os.environ.get("ALFRED_BRONZE_PRESERVE_TAIL", "3"))
BRONZE_CTX_RATIO = float(os.environ.get("ALFRED_BRONZE_CTX_RATIO", "0.61"))
TOKEN_THRESHOLD_DEFAULT = int(os.environ.get("ALFRED_BRONZE_TOKEN_THRESHOLD", "20000"))
SPECIALIST_NUM_CTX_DEFAULT = int(os.environ.get("ALFRED_SPECIALIST_NUM_CTX", "32768"))

_BRONZE_BUDGET_PATHS = (
    Path(os.environ.get("ALFRED_BRONZE_BUDGETS", "/app/config/bronze_budgets.yaml")),
)
_LITELLM_CONFIG_PATHS = (
    Path(os.environ.get("ALFRED_LITELLM_CONFIG", "/app/config/config.yaml")),
)
_budget_cache: dict[str, Any] = {"mtime": None, "map": {}}

_SUMMARIZE_INSTRUCTION = (
    "Summarize the following project context into technical bullet points. "
    "Focus on paths touched, tools used, findings, and open next steps. "
    "Do not invent domains or continue the dialogue."
)

_FIM_SUMMARY_PROMPT = (
    "### Task\nExtract facts from the transcript into bullet points only.\n"
    "Rules: use only facts present below; never invent paths/domains.\n\n"
    "### Transcript\n{transcript}\n\n### Summary\n"
)


def _normalize_model(model: str) -> str:
    m = (model or "").strip()
    if "/" in m:
        m = m.rsplit("/", 1)[-1]
    return m


def _threshold_for_ctx(num_ctx: int) -> int:
    return max(2048, int(num_ctx * BRONZE_CTX_RATIO))


def _load_bronze_budget_map() -> dict[str, dict[str, int]]:
    path = next((p for p in _BRONZE_BUDGET_PATHS if p.is_file()), None)
    mtime = path.stat().st_mtime if path else None
    if _budget_cache["map"] and _budget_cache["mtime"] == mtime:
        return _budget_cache["map"]  # type: ignore[return-value]

    out: dict[str, dict[str, int]] = {}
    if path is not None:
        try:
            import yaml

            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for name, row in (raw or {}).items():
                if not isinstance(row, dict) or str(name).startswith("_"):
                    continue
                nctx = int(row.get("num_ctx") or 0)
                if nctx <= 0:
                    continue
                thr = int(row.get("compress_threshold") or _threshold_for_ctx(nctx))
                out[str(name)] = {"num_ctx": nctx, "compress_threshold": thr}
        except Exception as exc:  # noqa: BLE001
            log.warning("bronze_budgets load failed: %s", exc)

    for cfg in _LITELLM_CONFIG_PATHS:
        if not cfg.is_file():
            continue
        try:
            import yaml

            data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
            for row in data.get("model_list") or []:
                name = str(row.get("model_name") or "")
                if not name or name in out:
                    continue
                lp = row.get("litellm_params") or {}
                opts = ((lp.get("extra_body") or {}).get("options")) or {}
                nctx = opts.get("num_ctx") or (row.get("model_info") or {}).get(
                    "max_input_tokens"
                )
                try:
                    nctx_i = int(nctx)
                except (TypeError, ValueError):
                    continue
                if nctx_i > 0:
                    out[name] = {
                        "num_ctx": nctx_i,
                        "compress_threshold": _threshold_for_ctx(nctx_i),
                    }
        except Exception as exc:  # noqa: BLE001
            log.warning("config num_ctx scan failed: %s", exc)
        break

    _budget_cache["mtime"] = mtime
    _budget_cache["map"] = out
    return out


def _bronze_budget(request_model: str) -> tuple[int, int]:
    bare = _normalize_model(request_model)
    row = _load_bronze_budget_map().get(bare)
    if row is None and bare.endswith("-fc"):
        row = _load_bronze_budget_map().get(bare[: -len("-fc")])
    if row:
        return int(row["compress_threshold"]), int(row["num_ctx"])
    if bare in {FIM_ALIAS, FIM_TAG}:
        return _threshold_for_ctx(8192), 8192
    return TOKEN_THRESHOLD_DEFAULT, SPECIALIST_NUM_CTX_DEFAULT


def _msg_text(msg: dict[str, Any]) -> str:
    content = msg.get("content") or ""
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(str(p.get("text") or ""))
            elif isinstance(p, str):
                parts.append(p)
        return "\n".join(parts)
    return str(content)


def _count_tokens(model: str, messages: list[dict[str, Any]]) -> int:
    try:
        import litellm

        return int(
            litellm.token_counter(model=model or "gpt-3.5-turbo", messages=messages) or 0
        )
    except Exception:  # noqa: BLE001
        return sum(len(_msg_text(m)) // 4 for m in messages or [])


def _estimate_request_tokens(
    model: str, messages: list[dict[str, Any]], tools: list | None
) -> int:
    n = _count_tokens(model, messages)
    if tools:
        n += len(json.dumps(tools)) // 4
    return n


def _split_for_bronze(
    messages: list[dict[str, Any]],
) -> tuple[list, list, list] | None:
    if len(messages) < PRESERVE_TAIL + 2:
        return None
    systems = [m for m in messages if m.get("role") == "system"]
    non_sys = [m for m in messages if m.get("role") != "system"]
    if len(non_sys) <= PRESERVE_TAIL:
        return None
    middle = non_sys[: -PRESERVE_TAIL]
    tail = non_sys[-PRESERVE_TAIL:]
    if not middle:
        return None
    return systems, middle, tail


def _middle_as_plaintext(middle: list[dict[str, Any]], max_chars: int) -> str:
    lines = []
    for m in middle:
        lines.append(f"{m.get('role', '?')}: {_msg_text(m)}")
    blob = "\n".join(lines)
    if len(blob) > max_chars:
        blob = blob[:max_chars] + "\n…[truncated for summarizer context]…"
    return blob


def _extractive_summary(middle: list[dict[str, Any]], *, max_bullets: int = 12) -> str:
    bullets: list[str] = []
    path_re = re.compile(r"(/[\w./_-]{6,})")
    for m in middle:
        text = _msg_text(m)
        for p in path_re.findall(text)[:2]:
            bullets.append(f"- Path: {p}")
        if len(bullets) >= max_bullets:
            break
    if not bullets:
        bullets.append(f"- (extractive) {len(middle)} prior message(s) omitted")
    return "\n".join(bullets[:max_bullets])


def _summary_looks_usable(summary: str, *, extractive: bool = False) -> bool:
    text = (summary or "").strip()
    if len(text) < 20:
        return False
    if extractive:
        return True
    bad = ("as an ai", "i cannot", "i'm sorry", "proceed to inspect")
    return not any(b in text.lower() for b in bad)


async def _summarize_fim(client: Any, middle_text: str) -> str:
    payload = {
        "model": FIM_TAG,
        "prompt": _FIM_SUMMARY_PROMPT.format(transcript=middle_text),
        "stream": False,
        "keep_alive": -1,
        "options": {"num_ctx": 8192, "temperature": 0.2, "num_predict": 512},
    }
    resp = await client.post(f"{OLLAMA}/api/generate", json=payload, timeout=120.0)
    resp.raise_for_status()
    content = ((resp.json() or {}).get("response") or "").strip()
    if content and not content.startswith("-"):
        content = "- " + content
    if not content or not _summary_looks_usable(content):
        raise RuntimeError("unusable FIM summary")
    return content


async def _ingest_bronze_optional(summary: str) -> None:
    if not CHROMA:
        return
    try:
        import httpx

        ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        doc_id = f"bronze-ctx:{uuid.uuid4().hex[:12]}"
        async with httpx.AsyncClient() as client:
            emb = await client.post(
                f"{OLLAMA}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": summary[:5500]},
                timeout=180.0,
            )
            emb.raise_for_status()
            vec = (emb.json() or {}).get("embedding")
            if not vec:
                return
            cols = await client.get(f"{CHROMA}/collections", timeout=30.0)
            cols.raise_for_status()
            coll_id = None
            for c in cols.json() or []:
                if c.get("name") == BRONZE_COLLECTION:
                    coll_id = c["id"]
                    break
            if not coll_id:
                created = await client.post(
                    f"{CHROMA}/collections",
                    json={"name": BRONZE_COLLECTION, "get_or_create": True},
                    timeout=30.0,
                )
                created.raise_for_status()
                coll_id = (created.json() or {}).get("id")
            if not coll_id:
                return
            # Chroma rejects nulls — use "" / False / 0. Teaching metadata only;
            # private labs often add dual keys (collection_tier) + richer fields.
            meta = {
                "tier": "bronze",
                "collection_tier": "bronze",
                "note_kind": "rolling-summary",
                "repo_tag": "",
                "created_at": ts,
                "last_accessed_at": ts,
                "is_pinned": False,
                "promotion_score": 0,
                "superseded_by": "",
                "review_status": "",
            }
            await client.post(
                f"{CHROMA}/collections/{coll_id}/upsert",
                json={
                    "ids": [doc_id],
                    "documents": [f"Bronze Context Summary ({ts}):\n{summary}"],
                    "metadatas": [meta],
                    "embeddings": [vec],
                },
                timeout=120.0,
            )
        log.info("bronze ingest ok id=%s", doc_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("bronze ingest skipped: %s", exc)


async def _maybe_bronze_compress(
    client: Any,
    *,
    request_model: str,
    messages: list[dict[str, Any]],
    tools: list | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    threshold, specialist_ctx = _bronze_budget(request_model)
    n_tok = _estimate_request_tokens(request_model, messages, tools)
    if n_tok <= threshold:
        return messages, None
    split = _split_for_bronze(messages)
    if split is None:
        return messages, None
    systems, middle, tail = split
    summary: str | None = None
    try:
        summary = await _summarize_fim(
            client, _middle_as_plaintext(middle, 10_000)
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("FIM summarize failed (%s) — extractive", exc)
        summary = _extractive_summary(middle)
        if not _summary_looks_usable(summary, extractive=True):
            summary = (
                f"(auto) Prior {len(middle)} message(s) dropped to protect "
                f"num_ctx={specialist_ctx}."
            )
    bronze_msg = {
        "role": "system",
        "content": f"[Bronze rolling summary]\n{summary}",
    }
    return [*systems, bronze_msg, *tail], summary


class AlfredBronzeMiddleware(CustomLogger):
    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> Any:
        if call_type not in {"completion", "acompletion"}:
            return data
        messages = list(data.get("messages") or [])
        if not messages:
            return data
        model = str(data.get("model") or "")
        tools = data.get("tools")
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                new_msgs, summary = await _maybe_bronze_compress(
                    client,
                    request_model=model,
                    messages=messages,
                    tools=tools if isinstance(tools, list) else None,
                )
            data["messages"] = new_msgs
            if summary:
                # Await so the task is not dropped when the hook returns.
                # Failures are swallowed inside _ingest_bronze_optional.
                await _ingest_bronze_optional(summary)
        except Exception as exc:  # noqa: BLE001
            log.warning("bronze compress unexpected: %s", exc)
        return data


proxy_handler_instance = AlfredBronzeMiddleware()
