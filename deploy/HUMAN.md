# Human deploy (Alfred template)

## Requirements

- Docker + Compose
- NVIDIA Container Toolkit **or** `ALFRED_CPU=1`
- Disk for model weights

## Steps

1. Clone this repo.
2. Run bootstrap:
   ```bash
   ./scripts/bootstrap.sh
   # edit deploy/compose/.env — set LITELLM_MASTER_KEY
   ./scripts/smoke.sh
   ```
3. Point Continue / Open WebUI at `http://127.0.0.1:4000/v1` with the master key.
4. Prefer aliases: `alfred-coder`, `alfred-reasoner`, `alfred-technical-planner`.
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

## Optional depth

- [docs/LEARNING_PATH.md](../docs/LEARNING_PATH.md) — eval / Sentinel / memory tiers (skeletons under `examples/`)
- [docs/guides/wire-middleware.md](../docs/guides/wire-middleware.md) — twin env knobs
