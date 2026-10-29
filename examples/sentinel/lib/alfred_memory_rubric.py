"""Minimal memory-rubric helpers for the public Sentinel template.

Full private labs often densify this module. Defaults keep JSON parsing +
routing thresholds without publishing estate-specific skill trees.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

RUBRIC_SYSTEM_PROMPT = (
    "Score ONE learning for skill promotion. Reply ONLY with JSON: "
    "debugging_friction, cross_project_reusability, verification_status, "
    "actionability_density (integers 1-5), domain, slug, skill_card."
)
RUBRIC_RESPONSE_FORMAT = {"type": "json_object"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class RubricScore:
    debugging_friction: int
    cross_project_reusability: int
    verification_status: int
    actionability_density: int
    domain: str
    slug: str
    skill_card: str

    @property
    def total(self) -> int:
        return (
            self.debugging_friction
            + self.cross_project_reusability
            + self.verification_status
            + self.actionability_density
        )


def _strip_fence(raw: str) -> str:
    t = (raw or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def parse_rubric_response(raw: str) -> RubricScore:
    data = json.loads(_strip_fence(raw))
    return RubricScore(
        debugging_friction=int(data["debugging_friction"]),
        cross_project_reusability=int(data["cross_project_reusability"]),
        verification_status=int(data["verification_status"]),
        actionability_density=int(data["actionability_density"]),
        domain=str(data.get("domain") or "general"),
        slug=str(data.get("slug") or "learning"),
        skill_card=str(data.get("skill_card") or ""),
    )


def route_score(score: RubricScore) -> str:
    if score.total < 8:
        return "purge"
    if score.total < 15:
        return "silver_pin"
    return "gold_stage"


def gold_skill_already_exists(score: RubricScore) -> str | None:
    root = Path(os.environ.get("ALFRED_SKILLS_ROOT", "./skills"))
    for cand in (root / score.slug, root / score.domain):
        if (cand / "SKILL.md").is_file():
            return str(cand)
    return None


def stage_gold_promotion(score: RubricScore) -> Path:
    out = Path(os.environ.get("STAGED_PROMOTIONS", "./alfred-data/staged_promotions"))
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{score.domain}_{score.slug}.md"
    path.write_text(score.skill_card or f"# {score.slug}\n", encoding="utf-8")
    return path


def digest_promotion_block(score: RubricScore, staged: Path) -> str:
    return (
        f"#### Gold candidate `{score.domain}/{score.slug}` (score={score.total})\n\n"
        f"Staged: `{staged}`\n\n"
        f"```text\n#domain:{score.domain}\nApply or ignore this staged skill card.\n```\n"
    )


def dedupe_promotion_blocks(blocks: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for b in blocks:
        key = b.strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(b)
    return out


