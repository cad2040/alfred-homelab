"""Minimal domain-tag helpers for the public Sentinel template."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DOMAIN_TAG_SYSTEM_PROMPT = (
    "You are a domain registrar. Suggest one kebab-case domain id for the note. "
    "Reply ONLY JSON: suggested_domain, is_new (bool), confidence (1-5), "
    "rationale, alternate_domains (array)."
)
DOMAIN_TAG_RESPONSE_FORMAT = {"type": "json_object"}


@dataclass
class DomainSuggestion:
    suggested_domain: str
    is_new: bool
    confidence: int
    rationale: str
    alternate_domains: list[str] = field(default_factory=list)


def load_known_domains(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or Path(os.environ.get("ALFRED_DOMAINS_YAML", "./routing/domains.yaml"))
    if not p.is_file():
        return []
    try:
        import yaml  # optional
    except ImportError:
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return list(data.get("domains") or [])


def known_domain_ids(domains: list[dict[str, Any]] | None = None) -> set[str]:
    rows = domains if domains is not None else load_known_domains()
    out: set[str] = set()
    for d in rows:
        if isinstance(d, dict) and d.get("id"):
            out.add(str(d["id"]))
    return out


def needs_domain_tag(meta: dict, known_ids: set[str] | None = None) -> bool:
    known_ids = known_ids or set()
    tag = str(meta.get("repo_tag") or meta.get("domain") or "").strip()
    if not tag or tag in {"unknown", "none"}:
        return True
    return bool(known_ids) and tag not in known_ids


def build_domain_tag_user_prompt(doc: str, known: list[dict], current_tag: str = "unknown") -> str:
    ids = [str(d.get("id")) for d in known if isinstance(d, dict) and d.get("id")]
    return (
        f"Current tag: {current_tag}\nKnown domains: {', '.join(ids[:40]) or '(none)'}\n\n"
        f"Document:\n{doc[:4000]}"
    )


def parse_domain_tag_response(raw: str, known_ids: set[str]) -> DomainSuggestion:
    t = (raw or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    data = json.loads(t)
    suggested = str(data.get("suggested_domain") or "general").strip()
    is_new = bool(data.get("is_new"))
    if suggested in known_ids:
        is_new = False
    return DomainSuggestion(
        suggested_domain=suggested,
        is_new=is_new,
        confidence=int(data.get("confidence") or 1),
        rationale=str(data.get("rationale") or ""),
        alternate_domains=[str(x) for x in (data.get("alternate_domains") or [])],
    )


def apply_suggestion_to_meta(meta: dict, suggestion: DomainSuggestion, staged_path: str = "") -> dict:
    out = dict(meta)
    out["repo_tag"] = suggestion.suggested_domain
    out["domain"] = suggestion.suggested_domain
    if staged_path:
        out["domain_proposal_path"] = staged_path
    return out


def ensure_domain_line(doc: str, domain: str) -> str:
    line = f"#domain:{domain}"
    if line in doc:
        return doc
    return f"{line}\n{doc}"


def stage_domain_proposal(suggestion: DomainSuggestion, bronze_id: str = "") -> Path:
    out = Path(os.environ.get("STAGED_DOMAIN_PROPOSALS", "./alfred-data/staged_promotions/domains"))
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{suggestion.suggested_domain}.md"
    path.write_text(
        f"# Proposed domain `{suggestion.suggested_domain}`\n\n"
        f"confidence={suggestion.confidence}\n\n{suggestion.rationale}\n",
        encoding="utf-8",
    )
    return path


def digest_domain_tag_section(results: list[dict]) -> str:
    if not results:
        return "_No Bronze domain-tag reviews this run._"
    lines = ["| Bronze | Domain | New? | Conf |", "| --- | --- | --- | ---: |"]
    for r in results:
        lines.append(
            f"| `{r.get('bronze_id')}` | `{r.get('suggested_domain')}` | "
            f"{r.get('is_new')} | {r.get('confidence')} |"
        )
    return "\n".join(lines)
