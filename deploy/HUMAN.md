# Human deploy (example stack)

## Requirements

- Docker + Compose
- NVIDIA Container Toolkit **or** use the CPU override
- Disk for model weights

## Steps

1. Clone this repo; read [docs/LEARNING_PATH.md](../docs/LEARNING_PATH.md).
2. `cp deploy/compose/.env.example deploy/compose/.env` and set `LITELLM_MASTER_KEY`.
3. Start stack:
   ```bash
   cd deploy/compose
   docker compose up -d
   # CPU-only:
   # docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d
   ```
   If CPU Docker still complains about NVIDIA devices, edit `docker-compose.yml` and **delete** the `ollama.deploy.resources` block (the cpu override empties `devices` but some engines still require the toolkit).
4. Pull models:
   ```bash
   docker exec alfred-ollama-example ollama pull qwen2.5:7b-instruct
   # optional FIM for Bronze /api/generate summaries:
   docker exec alfred-ollama-example ollama pull qwen2.5-coder:1.5b-base
   ```
5. Smoke gateway (re-verify on your host — LiteLLM callback APIs drift):
   ```bash
   set -a; source .env; set +a
   docker compose ps
   curl -s http://127.0.0.1:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY" | head
   curl -s http://127.0.0.1:4000/v1/chat/completions \
     -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"alfred-coder","messages":[{"role":"user","content":"#domain:docker-ufw\nWhy is UFW not enough for Docker publishes?"}],"max_tokens":200}'
   ```
   Expect a reply that mentions **DOCKER-USER** (skill inject). If LiteLLM logs show callback import errors, check `PYTHONPATH` mounts in compose.
6. Point Continue / Open WebUI at `http://127.0.0.1:4000/v1`.

## Callbacks

Compose mounts teaching middleware from `reference/litellm/` (skill inject + Bronze + optional persona). Details: [docs/guides/wire-middleware.md](../docs/guides/wire-middleware.md).

Disable persona: `ALFRED_PERSONA=` in compose env, or remove `custom_prompt.prompt_management` from `litellm/config.yaml` callbacks.

## Harden before LAN exposure

- Keep publishes on `127.0.0.1` until you understand DOCKER-USER (`skills/docker-ufw`).
- Never put real master keys in git.
- Add your own backup/DR — this example has none.

## Next

- [docs/guides/eval-harness.md](../docs/guides/eval-harness.md) + `examples/harness/` (keyword toy)
- [docs/guides/nightly-sentinel.md](../docs/guides/nightly-sentinel.md) + `examples/sentinel/` (skeleton)
- [docs/guides/model-challenge-wire-drop.md](../docs/guides/model-challenge-wire-drop.md) (pattern; CLIs private)
- [docs/guides/memory-tiers-curation.md](../docs/guides/memory-tiers-curation.md) (gates; prune cron private)
