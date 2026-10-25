# Agent deploy playbook (Alfred Homelab example)

You are helping a human stand up or adapt an **Alfred-like** local LLM stack from this public repo. Their private estate (if any) is out of scope unless they paste paths.

## Goals

1. Bring up `deploy/compose` safely (localhost binds).
2. Pull a chat model matching `litellm/config.yaml`.
3. Verify `/v1/models` + a tiny chat completion.
4. Point them at architecture + Gold skill examples — do not invent domains.

## Hard constraints

1. **Never** commit `.env` or real `LITELLM_MASTER_KEY` values.
2. **Never** change Compose publishes to `0.0.0.0` without explicit human approval + firewall plan (`skills/docker-ufw`).
3. **Never** `ollama rm` baseline tags the human still uses.
4. **Never** invent `#domain:` IDs; only use skills shipped here or the human’s registry.
5. Prefer **aliases** (`alfred-coder`) in client config, not raw Ollama tags.
6. Destructive host scripts → follow `skills/safe-script-production` (dry-run, `CONFIRM=yes`).
7. If wiring a new model, update Bronze budgets when `num_ctx` changes (`docs/guides/bronze-budgets.md`).

## Procedure

1. Read `README.md`, `docs/LEARNING_PATH.md`, and `docs/architecture.md`.
2. Ensure Docker works; GPU → default compose; CPU → add `-f docker-compose.cpu.yml`.
3. `cp deploy/compose/.env.example deploy/compose/.env` — generate a random master key; do not echo it into chat logs if avoidable.
4. `docker compose -f deploy/compose/docker-compose.yml up -d` (plus cpu override if needed).
5. Pull instruct (+ optional FIM base) tags from config / HUMAN.md.
6. Smoke `/v1/models` and a `#domain:docker-ufw` chat completion.
7. Point human at wire-middleware, harness examples, Sentinel skeleton — do not invent estate paths.

## Out of scope (refuse or defer)

- Publishing their private estate repo
- Baby-monitor / personal IoT stacks
- Blind `iptables -F` or disabling UFW
- Claiming Gemini/judge scores authorize auto-rewire

## Success criteria

- Compose healthy; Ollama has the chat tag; LiteLLM answers on `127.0.0.1:4000`
- Human understands aliases + that small local models need skills/rails
- No secrets written into the git tree
