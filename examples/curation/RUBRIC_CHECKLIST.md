# Rubric checklist (Bronze → Silver / Gold stage)

Score each factor **1–5**. Total = sum (max **20**).

| Factor | 1 | 3 | 5 |
|--------|---|---|---|
| `debugging_friction` | Typo / one-liner | Needed a few turns | Multi-hour obscure hardware/config |
| `cross_project_reusability` | One repo/file | Same stack twice | Portable pattern |
| `verification_status` | Guess / vibe | Plausible | Confirmed on host/code |
| `actionability_density` | “look into X” | Partial steps | Crisp rule + copy-paste template |

## Route (do not skip hard gates)

| Condition | Route |
|-----------|-------|
| `verification_status` ≤ 2 | **purge** |
| `actionability_density` ≤ 2 | **purge** |
| friction≤2 **and** reuse≤2 **and** ver≤3 | **purge** |
| total < 8 | **purge** |
| 8 ≤ total < 15 (and not hard-purged) | **silver_pin** |
| total ≥ 15 but ver < 4 **or** action < 4 | **silver_pin** (not Gold) |
| total ≥ 15 **and** ver ≥ 4 **and** action ≥ 4 | **gold_stage** (HITL only) |

## After routing

- **purge** — delete Bronze chunk (free Chroma)
- **silver_pin** — write sticky Silver; remove or mark Bronze origin
- **gold_stage** — draft under `staged_promotions/`; **human** merges git Gold + ingest

Reference implementation of the router: [`route_score.py`](route_score.py). Full narrative: [docs/guides/memory-tiers-curation.md](../../docs/guides/memory-tiers-curation.md).
