# Agent deploy playbook (Alfred template)

You are helping a human stand up an **Alfred-like** local LLM stack from this
**deploy template**. Their private estate (if any) is out of scope unless they
paste paths.

## Goals

1. Run `./scripts/bootstrap.sh`, set `LITELLM_MASTER_KEY`, then `./scripts/smoke.sh`
   (`curl` required; GPU recommended — `ALFRED_CPU=1` is bring-up only).
2. Verify skill inject (`#domain:docker-ufw` → DOCKER-USER) and Coach phrase.
3. Point clients at `alfred-coder` / `alfred-reasoner` aliases on `127.0.0.1:4000`.
4. Treat Alfred as a **HITL co-pilot** — never an unsupervised implementer.

## Hard constraints

1. **Never** commit `.env` or real `LITELLM_MASTER_KEY` values.
2. **Never** change Compose publishes to `0.0.0.0` without explicit human approval + firewall plan (`skills/docker-ufw`).
3. **Never** `ollama rm` baseline tags the human still uses.
4. **Never** invent `#domain:` IDs; only use `routing/domains.yaml` / shipped skills.
5. Prefer **aliases** (`alfred-coder`) in client config, not raw Ollama tags.
6. Destructive host scripts → `skills/safe-script-production` (dry-run, `CONFIRM=yes`).
7. After skill/domain edits → `./scripts/sync-skills.sh`.
8. Do not soft-park or remove `coach-this-prompt`.

## Procedure

1. Read `README.md`, `docs/PRIVATE_VS_TEMPLATE.md`, `docs/architecture.md`.
2. `./scripts/bootstrap.sh` (CPU: `ALFRED_CPU=1 ./scripts/bootstrap.sh`).
3. Ensure `LITELLM_MASTER_KEY` is a long random string in `deploy/compose/.env`.
4. `./scripts/smoke.sh`.
5. Optional depth: `docs/LEARNING_PATH.md` + `examples/` — do not invent estate paths.

## Out of scope (refuse or defer)

- Publishing anyone’s private lab repo or secrets
- Personal / family IoT device stacks
- Blind `iptables -F` or disabling UFW
- Claiming judge scores authorize auto-rewire
- Adding search proxies, digests, or DR as if they ship here

## Success criteria

- Compose healthy; LiteLLM answers on `127.0.0.1:4000`
- Smoke passes (DOCKER-USER + Coach structure)
- Human understands: co-pilot, MAX_LOADED=1, thin skills, template ≠ private estate
- No secrets in the git tree
