# Sentinel — setup (public template)

Nightly host observer: flock → telemetry → optional LLM passes → morning digest →
optional mail/backup hooks. **Proposals only** — never git-push, never rewrite
production config from this job.

This package mirrors the *behaviour* of a private lab Sentinel with **no private
mounts, hostnames, LAN layouts, or credentials**. Everything path-related goes
under `ALFRED_DATA_ROOT` (default `./alfred-data`).

## Requirements

- Linux host (uses `/proc`, `ip`, `ping`, optional `nvidia-smi` / `docker`)
- Python 3.11+
- LiteLLM + Ollama reachable on localhost (see repo `deploy/`)
- Optional: Chroma HTTP API (only if `SENTINEL_ENABLE_MEMORY=1`)
- Optional: UniFi (or compatible) controller API key

```bash
cd examples/sentinel
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example /path/to/your/private.env   # keep outside git
```

## Layout

```text
examples/sentinel/
  alfred-sentinel.py          # thin orchestrator
  lib/                        # collectors, digest, telemetry, stubs
  SETUP.md                    # this file
  .env.example                # copy → private env (never commit filled values)
  requirements.txt
  crontab.example
  run-sentinel.sh             # loads env + runs orchestrator
```

Runtime state (created on first run):

```text
$ALFRED_DATA_ROOT/
  telemetry/telemetry.db
  digests/morning/YYYY-MM-DD.md
  locks/vram.lock
  staged_promotions/          # only if memory stage enabled
```

## Quick start

1. Copy `.env.example` to a **private** env file (outside this repo).
2. Set at least:
   - `ALFRED_DATA_ROOT` — writable directory for digests + SQLite
   - `LITELLM_MASTER_KEY` — same key LiteLLM expects
   - `ALFRED_LITELLM_BASE` — e.g. `http://127.0.0.1:4000`
3. Smoke:

```bash
export $(grep -v '^#' /path/to/private.env | xargs)   # or: set -a; source …; set +a
./run-sentinel.sh
# or: python3 alfred-sentinel.py
```

4. Confirm `$ALFRED_DATA_ROOT/digests/morning/$(date +%F).md` and a row in
   `telemetry.db`.

5. Install cron from `crontab.example` (idle hours; hold the VRAM flock).

## Feature flags (all default off / safe)

| Env | Effect |
|-----|--------|
| `SENTINEL_ENABLE_CONTROLLER_API=1` | Read-only controller snapshot + Controller NHS (needs API base + key) |
| `SENTINEL_ENABLE_MEMORY=1` | Bronze domain-tag + Stage-4 rubric against Chroma |
| `SENTINEL_ENABLE_EVAL_HOOKS=1` | Optional Mon/Sun hooks if you install an eval CLI |
| `SENTINEL_MAIL_CMD` | Executable that receives the digest path |
| `SENTINEL_BACKUP_CMD` | Shell command / wrapper after digest |
| `SENTINEL_DISK_MOUNTS` | Comma-separated mounts to chart (default `/`) |
| `SENTINEL_SERVICE_URLS` | Optional `name=url,...` HTTP soft-checks |
| `ALFRED_UNIFI_TARGETS` | Extra LAN ICMP targets (IPs/hostnames you choose) |
| `ALFRED_UNIFI_GATEWAY` | Override detected default gateway |

Without a LiteLLM master key, Sentinel still writes host telemetry + digest
stubs and skips LLM sections.

## Network / controller (optional)

ICMP is **fail-closed** for connectivity status. Controller API is additive.

1. Create an Integrations API key on your controller (UI).
2. Put base URL + key only in the private env file.
3. Set `SENTINEL_ENABLE_CONTROLLER_API=1`.
4. Leave `ALFRED_UNIFI_API_VERIFY_TLS=0` for typical self-signed local TLS, or
   `1` if you terminate with a trusted cert.

When enabled, collectors summarize `system` / `stat/health` / `stat/device` /
`stat/sta` (count), derive alerts, and compute a **snapshot Controller NHS**.
The stability LLM interprets those facts + ICMP — it must not invent endpoints.

Do **not** commit real LAN CIDRs, AP inventories, or gateway maps into this tree.

## Layout principle (anti-monolith)

Keep `alfred-sentinel.py` as a thin orchestrator; grow behaviour in `lib/`
modules (`alfred_controller_api`, `alfred_sentinel_prompts`, collectors, digest).
Prefer packages with `__init__` re-exports over a second 900-line script.

## Mail / backups

Wire your own helpers:

```bash
SENTINEL_MAIL_CMD=/usr/local/bin/my-mail-digest
SENTINEL_BACKUP_CMD=/usr/local/bin/my-backup-nightly
```

Helpers are out of scope for this public package (SMTP credentials stay private).

## Memory Stage 4 (optional)

Requires Chroma collections named by `ALFRED_BRONZE_COLLECTION` /
`ALFRED_GOLD_COLLECTION`, plus `routing/domains.yaml` (or
`ALFRED_DOMAINS_YAML`). Rubric + domain-tag modules here are **minimal stubs** —
swap in denser private copies if you maintain them elsewhere.

## Hard rules

1. Do not fight `MAX_LOADED=1` — wait on the flock.
2. Never git push / never auto-apply staged Gold or domains.
3. Digests are checklists for humans.
4. Secrets only in a private env file outside git.

## Related docs

- [guides/nightly-sentinel.md](../../docs/guides/nightly-sentinel.md)
- [PRIVATE_VS_TEMPLATE.md](../../docs/PRIVATE_VS_TEMPLATE.md)
- [memory-tiers-curation.md](../../docs/guides/memory-tiers-curation.md)
