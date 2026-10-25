# Nightly Sentinel (HITL ops agent)

Sentinel is a **scheduled, flock-guarded pipeline** that observes the lab, asks specialists for commentary, writes a morning digest, and optionally kicks backups / eval hooks. It is **not** allowed to silently rewrite production config or push git.

## Pipeline (reference stages)

```text
flock (VRAM / mutual exclusion)
  → collect telemetry / findings
  → security specialist pass (optional)
  → reasoner pass (stability / domain-tag suggestions)
  → write morning digest (markdown)
  → best-effort mail (msmtp etc. — private)
  → backup stages (private)
  → optional: schedule weekly eval matrix
```

Hard rules from real ops:

1. **Never unload the FIM pin** to run Sentinel.
2. **Never git push** from Sentinel.
3. Digests and staged promotions are **proposals** — humans apply.
4. Hold a **VRAM flock** so chat and nightly jobs don’t thrash slot-2.
5. Time it for idle hours (e.g. `0 2 * * *`).

## What to put in a digest

- Disk / container / GPU snapshots you already trust
- Security findings phrased as checklists
- “Consider wiring model X” — never auto-pull
- Links to staged files under a promotions directory

## Skeleton in this repo

**Scope:** a digest writer with flock + LiteLLM chat. No telemetry collectors, mail, backups, or memory prune — those are private stages you add later.

[`examples/sentinel/sentinel_skeleton.py`](../../examples/sentinel/sentinel_skeleton.py) demonstrates:

- env-based config (no hardcoded estate paths)
- flock
- LiteLLM chat call to `alfred-reasoner`
- writing `DIGEST_DIR/YYYY-MM-DD.md`
- refusing to unload FIM

Cron example: [`examples/sentinel/crontab.example`](../../examples/sentinel/crontab.example).

## Growing toward a full Sentinel

Port privately, one stage at a time:

1. Telemetry DB / `docker ps` / `ollama ps`
2. Security alias with a strict system prompt
3. Domain-tag suggestions against your registry
4. Memory rubric → purge Bronze noise / pin Silver / stage Gold drafts (human merge) — see [memory-tiers-curation.md](memory-tiers-curation.md)
5. Backup scripts you already trust
6. Hook to weekly eval after flock release

Keep SMTP credentials and host UUIDs in private env — never in a public tree.
