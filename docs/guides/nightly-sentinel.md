# Nightly Sentinel (HITL ops agent)

Sentinel is a **scheduled, flock-guarded pipeline** that observes the host, asks
specialists for commentary, writes a morning digest, and optionally kicks mail /
backup / eval hooks. It is **not** allowed to silently rewrite production config
or push git.

**In this repo:** a sanitized, runnable package under
[`examples/sentinel/`](../../examples/sentinel/) — same stages as a private lab
build, with **env-driven paths** and **no private mounts, LAN maps, or secrets**.

## Pipeline

```text
flock (VRAM / mutual exclusion)
  → collect telemetry / findings (SQLite under ALFRED_DATA_ROOT)
  → security specialist pass (optional; needs LiteLLM key)
  → reasoner pass (stability)
  → optional memory Stage 4 (off by default)
  → write morning digest (markdown)
  → optional mail / backup / eval hooks (your wrappers)
```

Hard rules:

1. **Do not fight MAX_LOADED=1** — wait for the flock.
2. **Never git push** from Sentinel.
3. Digests and staged promotions are **proposals** — humans apply.
4. Hold a **VRAM flock** so chat and nightly jobs do not thrash the single resident.
5. Time it for idle hours (e.g. `15 2 * * *`).

## Setup

Full instructions: [`examples/sentinel/SETUP.md`](../../examples/sentinel/SETUP.md).

```bash
cd examples/sentinel
cp .env.example /path/to/private/sentinel.env   # fill secrets offline
export ALFRED_ENV_FILE=/path/to/private/sentinel.env
./run-sentinel.sh
```

Cron: [`examples/sentinel/crontab.example`](../../examples/sentinel/crontab.example).

## What lands in a digest

- Disk / container / GPU / RAM snapshots
- ICMP network health (fail-closed) + optional controller API snapshot
- Deterministic **Controller NHS** (0–100) from collected API facts when enabled
- Stability pass: host brief + grounded network assessment (inventory, anomalies,
  capacity, ICMP-adjusted NHS) — no invented `/stat/*` metrics
- Security findings as checklists
- “Consider model X” on the 1st — never auto-pull
- Optional coached prompt blocks for Open WebUI / Cline

## Feature flags

Defaults are safe / off for anything that needs private infra:

| Flag | Default | Notes |
|------|---------|--------|
| `SENTINEL_ENABLE_CONTROLLER_API` | `0` | Controller API snapshot + Controller NHS |
| `SENTINEL_ENABLE_MEMORY` | `0` | Chroma Bronze/Gold Stage 4 |
| `SENTINEL_ENABLE_EVAL_HOOKS` | `0` | Mon/Sun optional CLI |
| `SENTINEL_MAIL_CMD` / `SENTINEL_BACKUP_CMD` | unset | Your private wrappers |

## Growing further

1. Point `SENTINEL_DISK_MOUNTS` and ICMP targets at **your** lab (private env only).
2. Wire mail + backup wrappers you already trust.
3. Enable memory only after Chroma + domains registry exist.
4. Densify rubric / domain-tag modules privately if the stubs are too thin.

Keep SMTP credentials, API keys, host UUIDs, and personal directory trees out of
git — see [PRIVATE_VS_TEMPLATE.md](../PRIVATE_VS_TEMPLATE.md).
