#!/usr/bin/env python3
"""Sanitized Bronze → Silver / Gold-stage router (teach the gates).

Deterministic gates sit *above* total thresholds so a generous small model
cannot silver-pin vague or unverified notes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RubricScore:
    debugging_friction: int
    cross_project_reusability: int
    verification_status: int
    actionability_density: int

    @property
    def total(self) -> int:
        return (
            self.debugging_friction
            + self.cross_project_reusability
            + self.verification_status
            + self.actionability_density
        )


def route_score(score: RubricScore) -> str:
    """Return purge | silver_pin | gold_stage."""
    if score.verification_status <= 2:
        return "purge"
    if score.actionability_density <= 2:
        return "purge"
    if (
        score.debugging_friction <= 2
        and score.cross_project_reusability <= 2
        and score.verification_status <= 3
    ):
        return "purge"

    if score.total < 8:
        return "purge"
    if score.total < 15:
        return "silver_pin"

    if score.verification_status < 4:
        return "silver_pin"
    if score.actionability_density < 4:
        return "silver_pin"
    return "gold_stage"


if __name__ == "__main__":
    demos = [
        RubricScore(2, 2, 2, 2),  # purge — vague
        RubricScore(4, 3, 3, 3),  # silver (total 13)
        RubricScore(5, 4, 3, 4),  # silver — high total but ver < 4
        RubricScore(5, 4, 4, 4),  # gold_stage (HITL)
    ]
    for s in demos:
        print(f"total={s.total:2d} → {route_score(s)}")
