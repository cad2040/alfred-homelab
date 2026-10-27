# Human deploy (Alfred template)

## Requirements

- Docker + Compose
- **GPU recommended** (NVIDIA Container Toolkit). `ALFRED_CPU=1` starts the
  stack but 14B/9B inference is not practical day-to-day.
- Disk for model weights (tens of GB for the reference pulls)
- `curl` for `scripts/smoke.sh` (`python3` or `jq` optional for pretty-print)

## Steps

1. Clone this repo.
2. Run bootstrap (large model pulls — plan disk/time):
   ```bash
   ./scripts/bootstrap.sh
   # edit deploy/compose/.env — set LITELLM_MASTER_KEY to a long random string
   ./scripts/smoke.sh
   ```
3. Point Continue / Open WebUI at `http://127.0.0.1:4000/v1` with the master key.
4. Prefer aliases: `alfred-coder`, `alfred-reasoner`, `alfred-technical-planner`,
   `alfred-security` (see [docs/architecture.md](../docs/architecture.md)).
5. Try `#domain:docker-ufw` and `Coach this Prompt:` (smoke already covers both).

## Co-pilot (not an agent)

- Alfred **drafts**; you **review and debug**.
- Spec Kit / plans: human edits until true; hand **one task** to coder.
- Never treat digests or skill inject as auto-authority.

## After skill edits

```bash
./scripts/sync-skills.sh
./scripts/smoke.sh
```

## Harden before LAN exposure

- Keep publishes on `127.0.0.1` until DOCKER-USER is understood (`skills/docker-ufw`).
- Never commit real master keys.
- Add your own backup/DR — this template has none.

## What this template is not

Search proxies, nightly digests/mail, Chroma ingest cron, personal IoT skills,
and DR stay **out of tree** on purpose. See
[docs/PRIVATE_VS_TEMPLATE.md](../docs/PRIVATE_VS_TEMPLATE.md).

## Optional depth

- [docs/LEARNING_PATH.md](../docs/LEARNING_PATH.md) — eval / Sentinel / memory tiers (skeletons under `examples/`)
- [docs/guides/wire-middleware.md](../docs/guides/wire-middleware.md) — twin env knobs
