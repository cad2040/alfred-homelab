"""Teaching skill-inject callback for LiteLLM (sanitized public extract).

Looks for ``#domain:<id>`` in the latest user message, loads matching
``skills/<id>/SKILL.md`` (or ``skills/<id>.md``), and prepends them as a
system message up to ``ALFRED_MAX_SKILL_CHARS`` (default 4500).

Optional ``domains.yaml`` maps phrase substrings → domain id when no tag.

Wire-up: see ``docs/guides/wire-middleware.md``.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

try:
    from litellm.integrations.custom_logger import CustomLogger
except Exception:  # noqa: BLE001
    from litellm.proxy.hooks.callback import CustomLogger  # type: ignore

log = logging.getLogger("alfred.routing.skills")

DOMAIN_RE = re.compile(r"#domain:([a-z0-9][a-z0-9_-]*)", re.I)
MAX_SKILL_CHARS = int(os.environ.get("ALFRED_MAX_SKILL_CHARS", "4500"))
SKILLS_ROOT = Path(
    os.environ.get(
        "ALFRED_SKILLS_ROOT",
        "/app/skills",
    )
)
DOMAINS_YAML = Path(
    os.environ.get("ALFRED_DOMAINS_YAML", "/app/config/domains.yaml")
)


def _latest_user_text(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages or []):
        if msg.get("role") != "user":
            continue
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
    return ""


def _load_phrase_map() -> dict[str, str]:
    if not DOMAINS_YAML.is_file():
        return {}
    try:
        import yaml

        raw = yaml.safe_load(DOMAINS_YAML.read_text(encoding="utf-8")) or {}
        # Accept either {phrases: {substr: domain}} or flat {substr: domain}
        phrases = raw.get("phrases") if isinstance(raw, dict) else None
        src = phrases if isinstance(phrases, dict) else raw
        out = {}
        for k, v in (src or {}).items():
            if str(k).startswith("_"):
                continue
            out[str(k).lower()] = str(v).strip()
        return out
    except Exception as exc:  # noqa: BLE001
        log.warning("domains.yaml load failed: %s", exc)
        return {}


def _domains_for_text(user_text: str) -> list[str]:
    tags = [t.lower() for t in DOMAIN_RE.findall(user_text or "")]
    if tags:
        # preserve order, unique
        seen: set[str] = set()
        out = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out
    low = (user_text or "").lower()
    hits = []
    for phrase, domain in _load_phrase_map().items():
        if phrase and phrase in low:
            hits.append(domain)
    # unique
    seen = set()
    out = []
    for d in hits:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out[:3]


def _skill_path(domain_id: str) -> Path | None:
    candidates = [
        SKILLS_ROOT / domain_id / "SKILL.md",
        SKILLS_ROOT / f"{domain_id}.md",
        SKILLS_ROOT / domain_id / "skill.md",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _load_skill(domain_id: str) -> str | None:
    path = _skill_path(domain_id)
    if not path:
        log.info("no skill file for domain=%s under %s", domain_id, SKILLS_ROOT)
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    # Drop YAML frontmatter for inject compactness
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2].lstrip("\n")
    return text.strip()


class AlfredSkillRouting(CustomLogger):
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
        user_text = _latest_user_text(messages)
        domains = _domains_for_text(user_text)
        if not domains:
            return data

        blobs: list[str] = []
        used = 0
        for d in domains:
            body = _load_skill(d)
            if not body:
                continue
            chunk = f"### Gold skill `{d}`\n{body}"
            if blobs and used + len(chunk) > MAX_SKILL_CHARS:
                break
            if not blobs and len(chunk) > MAX_SKILL_CHARS:
                chunk = chunk[: MAX_SKILL_CHARS - 20] + "\n…[truncated]"
            blobs.append(chunk)
            used += len(chunk)

        if blobs:
            inject = (
                "Obey the following domain skill rules. "
                "Prefer them over generic advice.\n\n" + "\n\n".join(blobs)
            )
            messages.insert(0, {"role": "system", "content": inject})
            data["messages"] = messages
            data["_alfred_skill_domains"] = domains
            log.info("injected skills=%s chars=%s", domains, used)
        return data


proxy_handler_instance = AlfredSkillRouting()
