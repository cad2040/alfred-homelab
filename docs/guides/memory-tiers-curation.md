# Memory tiers & skill curation (Bronze → Silver → Gold)

How a rails-heavy lab keeps **Chroma useful** instead of becoming a junk drawer: capture freely at Bronze, auto-promote only to Silver under hard gates, and **never** write Gold skill cards without a human.

This is separate from **Bronze rolling chat compress** ([bronze-budgets.md](bronze-budgets.md)) — that protects `num_ctx`. This guide is about **long-term memory + Gold skills**.

**Scope of this repo:** the **gates, rubric checklist, and `route_score` demo**. The nightly promote-and-prune job, Mem0 Silver store, and staged Gold apply path live in a **private** lab. Optional Bronze→Chroma upsert from teaching middleware is best-effort only — it does not prune.

## Tier map

| Tier | Typical store | Who writes | Lifetime intent |
|------|---------------|------------|-----------------|
| **Bronze** | `ephemeral_working_context`, `bronze_context_log` | Chat wrap-ups, `ctx_note`, rolling summaries | Short-lived working memory |
| **Silver** | e.g. `mem0_alfred_silver` (or equivalent) | Nightly promote job | Sticky notes / entities — **not** law |
| **Gold** | `curated_skills_registry` + **git** `skills/<slug>/` | Human only (staged drafts OK) | Injectable domain law |

```text
capture (bronze)
    │
    ▼
nightly evaluate + rubric
    │
    ├─ purge          → delete bronze noise
    ├─ silver_pin     → sticky memory (auto OK)
    └─ gold_stage     → draft under staged_promotions/  ──HITL──► git Gold skill
```

## Bronze capture (automatic)

Sources that land as Bronze:

1. **Session wrap-ups / notes** (`ephemeral_working_context`) — deferred bugs, TODOs, `ctx_note`
2. **Rolling chat summaries** (`bronze_context_log`) — LiteLLM Bronze middleware upserts after compress
3. Optional other “working” collectors you add privately

Metadata discipline (Chroma rejects nulls — use `""` not `null`):

```text
collection_tier | repo_tag | created_at | last_accessed_at
is_pinned | promotion_score | superseded_by
```

Optional: `tier=bronze`, `note_kind`, `source`, `review_status`.

**Rule:** Bronze is allowed to be messy. The nightly job’s job is to **throw most of it away**.

## Silver self-promote (automatic, gated)

A nightly pass (see [nightly-sentinel.md](nightly-sentinel.md)):

1. Pull Bronze chunks not already `review_status ∈ {promoted, rejected, gold, silver}`
2. Pre-filter (too short, rejected, empty) → skip/delete
3. Score with the **4-factor rubric** (below)
4. Route:
   - **purge** → delete from Bronze (frees Chroma)
   - **silver_pin** → write Silver with `collection_tier=silver`, then delete/mark Bronze origin
5. **Never** invent a git Gold skill in this step

Silver is memory for recall (“we hit this before”), not an injectable `#domain:` card.

## Gold human-gated promote

Gold requires **all** of:

| Gate | Requirement |
|------|-------------|
| Rubric total | ≥ **15** / 20 |
| `verification_status` | ≥ **4** (tested/confirmed fix) |
| `actionability_density` | ≥ **4** (copy-paste rule/template) |
| Human confirm | Explicit — digest checkbox / PR / apply |
| Git SoT | `skills/<slug>/SKILL.md` (+ registry row) |
| Size caps | Inject SKILL ≤ ~4500; SKILL+ref ≤ ~5500 |

Automation may **stage** a draft under something like `staged_promotions/` and put a digest prompt in the morning mail. Humans merge into git, then ingest to `curated_skills_registry`.

**Never** auto-merge Gold from a 7B/9B rubric score alone — models are generous.

## 4-factor rubric

Each factor is an integer **1–5**. Total = sum (max 20).

| Factor | Low (1) | High (5) |
|--------|---------|----------|
| `debugging_friction` | Typo / obvious | Obscure multi-turn hardware/config |
| `cross_project_reusability` | One file | Portable across stacks |
| `verification_status` | Hypothesis | Confirmed on host/code |
| `actionability_density` | Vague note | Crisp rule + template |

### Deterministic router (teach this verbatim)

```text
HARD PURGE (even if total looks high):
  verification_status ≤ 2            → purge
  actionability_density ≤ 2          → purge
  friction≤2 AND reuse≤2 AND ver≤3   → purge

TOTAL BANDS:
  total < 8   → purge
  8 ≤ total < 15 → silver_pin   (unless hard purge)
  total ≥ 15  → still silver_pin unless ver≥4 AND action≥4
                else gold_stage
```

Vague “maybe GPU / felt slow / look later” notes must stay in the **purge** band.

## Pruning — keep Chroma free of rubbish

Without pruning, Bronze fills with rolling summaries and half-thoughts; retrieval gets worse, not better.

| Action | When |
|--------|------|
| Delete Bronze after successful Silver extract | Same nightly job |
| Purge low-rubric Bronze | Same job (`route=purge`) |
| TTL / age sweep (optional) | e.g. unpinned Bronze `created_at` > 21 days |
| Skip already routed | `review_status` in promoted/rejected/gold/silver |
| Supersede | Set `superseded_by` on old Gold when a denser skill replaces it; don’t leave duplicates |
| Pin sparingly | `is_pinned=true` only for durable Silver/Gold worth keeping through sweeps |

**Operator metric:** Bronze collection size should **sawtooth** (grow by day, shrink after nightly), not climb forever.

## Collections (example names)

Adapt names to your lab; keep the *roles*:

| Role | Example name |
|------|----------------|
| Working / wrap-ups | `ephemeral_working_context` |
| Rolling chat Bronze | `bronze_context_log` |
| Sticky Silver | `mem0_alfred_silver` |
| Injectable Gold | `curated_skills_registry` |

Gold **git** cards remain SoT; Chroma Gold is a search/inject cache — re-ingest after skill edits (`ingest` / sync script in your private lab).

## Minimal implement order (private lab)

1. Upsert Bronze with required metadata (middleware + wrap-up hooks).
2. Nightly: list Bronze → rubric JSON → purge / silver / stage-gold.
3. Digest lists staged Gold for HITL.
4. Human writes/merges `skills/<slug>/` → ingest Gold.
5. Add TTL prune once volume hurts.

Teaching hooks here: Sentinel skeleton ([nightly-sentinel.md](nightly-sentinel.md)) + rubric ([../../examples/curation/RUBRIC_CHECKLIST.md](../../examples/curation/RUBRIC_CHECKLIST.md)). Do not expect a full prune cron in this tree.
