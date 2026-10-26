"""LiteLLM pre-call routing (sanitized Alfred template twin).

Phrase / ``#domain:`` / keywords → preferred model + Gold skill inject.
Live-shaped after the private estate callback — **without** SearXNG, estate
paths, stack-monitor, or applicability judge (off by default).

Env:
  ALFRED_SKILLS_ROOT       default /app/skills
  ALFRED_DOMAINS_YAML      default /app/config/domains.yaml
  ALFRED_MAX_SKILL_CHARS   default 4500
  ALFRED_SKILL_CARDS_CHARS default 3000 (soft keyword path)
  ALFRED_WEBSEARCH         default 0 (SearXNG disabled in template)
  ALFRED_SKILL_JUDGE       default 0 (no LLM applicability judge)

Register: ``alfred_routing_callback.proxy_handler_instance``
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

log = logging.getLogger("alfred.routing")

SKILLS = Path(os.environ.get("ALFRED_SKILLS_ROOT", "/app/skills"))
DOMAINS_YAML = Path(
    os.environ.get("ALFRED_DOMAINS_YAML", "/app/config/domains.yaml")
)
MAX_SKILL_CHARS = int(os.environ.get("ALFRED_MAX_SKILL_CHARS", "4500"))
MAX_SKILL_CARDS_CHARS = int(os.environ.get("ALFRED_SKILL_CARDS_CHARS", "3000"))
WEBSEARCH_ENABLED = os.environ.get("ALFRED_WEBSEARCH", "0").strip() not in {
    "0",
    "",
    "false",
    "False",
    "no",
}
# Template: judge off. Private labs may set ALFRED_SKILL_JUDGE=1 later.
SKILL_JUDGE_ENABLED = os.environ.get("ALFRED_SKILL_JUDGE", "0").strip() in {
    "1",
    "true",
    "True",
    "yes",
}

DOMAIN_RE = re.compile(r"#domain:([a-z0-9][a-z0-9_-]*)", re.I)
_LOAD_SKILL_RE = re.compile(
    r"(?is)(?:#load_skill\b|load\s+skill:)\s*([a-z0-9][a-z0-9_-]*)"
)
UMBRELLA_DOMAIN_IDS = frozenset({"coding", "software-planning"})
_LEGACY_MODEL_ALIASES = {
    "alfred_technical_planner": "alfred-technical-planner",
}
_registry_cache: dict[str, Any] = {"mtime": None, "data": {}}


def _latest_user_text(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages or []):
        if msg.get("role") != "user":
            continue
        content = msg.get("content") or ""
        if isinstance(content, list):
            parts: list[str] = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append(str(p.get("text") or ""))
                elif isinstance(p, str):
                    parts.append(p)
            return "\n".join(parts)
        return str(content)
    return ""


def _phrase_triggered(hay: str, needle: str) -> bool:
    """Match phrase anywhere in the user text (Continue @file dumps prepend)."""
    if not needle:
        return False
    return needle in hay


def _load_registry() -> dict[str, Any]:
    if not DOMAINS_YAML.is_file():
        return {}
    mtime = DOMAINS_YAML.stat().st_mtime
    if _registry_cache["data"] and _registry_cache["mtime"] == mtime:
        return _registry_cache["data"]  # type: ignore[return-value]
    import yaml

    raw = yaml.safe_load(DOMAINS_YAML.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raw = {}
    _registry_cache["mtime"] = mtime
    _registry_cache["data"] = raw
    return raw


def resolve_route(user_text: str) -> tuple[str, list[str], str]:
    """Return (preferred_model, skill_names, match_reason)."""
    try:
        reg = _load_registry()
    except Exception as exc:  # noqa: BLE001
        log.warning("domains.yaml read failed: %s — fallback alfred-reasoner", exc)
        return "alfred-reasoner", [], "yaml-error"

    domains = {d["id"]: d for d in (reg.get("domains") or []) if isinstance(d, dict) and "id" in d}

    for trig in reg.get("phrase_triggers") or []:
        if not isinstance(trig, dict):
            continue
        phrase = trig.get("phrase") or ""
        if not phrase:
            continue
        hay = user_text if not trig.get("case_insensitive") else user_text.lower()
        needle = phrase if not trig.get("case_insensitive") else phrase.lower()
        if _phrase_triggered(hay, needle):
            dom = domains.get(trig.get("domain_id") or "")
            if dom:
                return (
                    dom.get("preferred_model") or "alfred-reasoner",
                    list(dom.get("skills") or []),
                    f"phrase:{phrase}",
                )

    tag_ids = [t.lower() for t in DOMAIN_RE.findall(user_text or "")]
    if tag_ids:
        skills: list[str] = []
        seen: set[str] = set()
        matched: list[str] = []
        model = "alfred-reasoner"
        for dom_id in tag_ids:
            dom = domains.get(dom_id)
            if not dom:
                continue
            matched.append(dom_id)
            if matched[0] == dom_id:
                model = dom.get("preferred_model") or model
            if dom_id in UMBRELLA_DOMAIN_IDS:
                continue
            for s in dom.get("skills") or []:
                if s not in seen:
                    seen.add(s)
                    skills.append(s)
        if matched:
            first = domains.get(matched[0]) or {}
            model = first.get("preferred_model") or model
            return model, skills, f"tag:{'+'.join(matched)}"

    lower = (user_text or "").lower()
    best = None
    best_hits = 0
    for dom in domains.values():
        dom_id = str(dom.get("id") or "")
        if dom_id in UMBRELLA_DOMAIN_IDS:
            continue
        skills = list(dom.get("skills") or [])
        if not skills:
            continue
        hits = 0
        for kw in dom.get("keywords") or []:
            k = str(kw).strip()
            if not k or k.startswith("#"):
                continue
            if " " not in k and len(k) < 5:
                continue
            if k.lower() in lower:
                hits += 1
        if hits > best_hits:
            best_hits = hits
            best = dom
    if best and best_hits > 0:
        return (
            best.get("preferred_model") or "alfred-reasoner",
            list(best.get("skills") or []),
            f"keywords:{best.get('id')}:{best_hits}",
        )

    return "alfred-reasoner", [], "fallback"


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text.strip()
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return parts[2].lstrip("\n").strip()
    return text.strip()


def _load_skill_body(skill_name: str) -> str | None:
    path = SKILLS / skill_name / "SKILL.md"
    if not path.is_file():
        # Allow skill id == domain folder alias (vram-runtime → same name)
        alt = SKILLS / f"{skill_name}.md"
        if alt.is_file():
            path = alt
        else:
            return None
    try:
        return _strip_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        log.warning("skill read failed %s: %s", skill_name, exc)
        return None


def _skill_description(skill_name: str) -> str:
    path = SKILLS / skill_name / "SKILL.md"
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    try:
        import yaml

        fm = yaml.safe_load(parts[1]) or {}
    except Exception:  # noqa: BLE001
        return ""
    desc = fm.get("description") if isinstance(fm, dict) else None
    if isinstance(desc, str):
        return " ".join(desc.split())
    return ""


def _build_skill_cards(highlight: list[str] | None = None) -> str:
    budget = MAX_SKILL_CARDS_CHARS
    if not SKILLS.is_dir() or budget <= 0:
        return ""
    hi = {h.lower() for h in (highlight or []) if h}
    lines: list[str] = [
        "### Alfred skill cards (soft catalog)",
        "Full Gold is NOT auto-loaded unless listed under must-obey. "
        "If a card applies, reply with `#load_skill <id>` on a line, then follow it.",
        "",
    ]
    used = sum(len(x) + 1 for x in lines)
    names = sorted(
        d.name
        for d in SKILLS.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and (d / "SKILL.md").is_file()
    )
    ordered = [n for n in names if n in hi] + [n for n in names if n not in hi]
    for name in ordered:
        desc = _skill_description(name) or "Alfred Gold skill"
        if len(desc) > 110:
            desc = desc[:107] + "..."
        star = "★ " if name in hi else ""
        line = f"- {star}`{name}` — {desc}"
        if used + len(line) + 1 > budget:
            lines.append("- … (card catalog truncated)")
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


def _is_hard_inject(match_reason: str) -> bool:
    return match_reason.startswith("phrase:") or match_reason.startswith("tag:")


def _inject_skills(
    messages: list[dict[str, Any]],
    skill_names: list[str],
    *,
    hard: bool,
    match_reason: str,
) -> list[dict[str, Any]]:
    blobs: list[str] = []
    used = 0
    load_extra = _LOAD_SKILL_RE.findall(_latest_user_text(messages))
    names = list(skill_names)
    for extra in load_extra:
        if extra not in names:
            names.append(extra)

    if hard and names:
        for name in names:
            body = _load_skill_body(name)
            if not body:
                continue
            chunk = f"### Gold skill `{name}` (must obey)\n{body}"
            if blobs and used + len(chunk) > MAX_SKILL_CHARS:
                break
            if not blobs and len(chunk) > MAX_SKILL_CHARS:
                chunk = chunk[: MAX_SKILL_CHARS - 20] + "\n…[truncated]"
            blobs.append(chunk)
            used += len(chunk)
        header = (
            "Obey the following domain skill rules. "
            "Prefer them over generic advice.\n\n"
        )
    else:
        # Soft path: cards + optional highlighted full skills if judge were on
        # (template: cards only; #load_skill still full-loads above).
        cards = _build_skill_cards(highlight=names)
        if cards:
            blobs.append(cards)
            used += len(cards)
        for name in load_extra:
            body = _load_skill_body(name)
            if not body:
                continue
            chunk = f"### Gold skill `{name}` (must obey — #load_skill)\n{body}"
            if used + len(chunk) > MAX_SKILL_CHARS:
                chunk = chunk[: max(0, MAX_SKILL_CHARS - used - 20)] + "\n…[truncated]"
            blobs.append(chunk)
            used += len(chunk)
        header = ""

    if not blobs:
        return messages
    inject = header + "\n\n".join(blobs)
    out = list(messages)
    out.insert(0, {"role": "system", "content": inject})
    log.info(
        "skill inject hard=%s reason=%s skills=%s chars=%s websearch=%s judge=%s",
        hard,
        match_reason,
        names,
        used,
        WEBSEARCH_ENABLED,
        SKILL_JUDGE_ENABLED,
    )
    return out


class AlfredRoutingCallback(CustomLogger):
    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> Any:
        if call_type not in {"completion", "acompletion"}:
            return data

        # Legacy Continue underscore alias
        model = str(data.get("model") or "")
        bare = model.rsplit("/", 1)[-1]
        if bare in _LEGACY_MODEL_ALIASES:
            data["model"] = _LEGACY_MODEL_ALIASES[bare]

        messages = list(data.get("messages") or [])
        user_text = _latest_user_text(messages)
        preferred, skills, reason = resolve_route(user_text)
        hard = _is_hard_inject(reason)

        # Soft rewrite of empty / fallback model only when client sent a bare alias
        # we recognise — do not override an explicit alfred-coder selection.
        req = bare if bare not in _LEGACY_MODEL_ALIASES else _LEGACY_MODEL_ALIASES[bare]
        if reason != "fallback" and preferred and req in {
            "alfred-reasoner",
            "alfred-coder",
            "alfred-technical-planner",
            "alfred-security",
            "",
        }:
            # Keep client-chosen specialist; only log preferred.
            data["_alfred_preferred_model"] = preferred

        data["messages"] = _inject_skills(
            messages, skills, hard=hard, match_reason=reason
        )
        data["_alfred_route"] = {
            "reason": reason,
            "skills": skills,
            "preferred_model": preferred,
            "hard": hard,
            "websearch": WEBSEARCH_ENABLED,
        }
        if WEBSEARCH_ENABLED:
            log.debug("websearch enabled but template has no SearXNG — no-op")
        return data


proxy_handler_instance = AlfredRoutingCallback()
