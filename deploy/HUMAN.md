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
4. Pull models:
   ```bash
   docker exec alfred-ollama-example ollama pull qwen2.5:7b-instruct
   # optional FIM for Bronze /api/generate summaries:
   docker exec alfred-ollama-example ollama pull qwen2.5-coder:1.5b-base
   ```
5. Smoke gateway:
   ```bash
   set -a; source .env; set +a
   curl -s http://127.0.0.1:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY" | head
   curl -s http://127.0.0.1:4000/v1/chat/completions \
     -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"alfred-coder","messages":[{"role":"user","content":"#domain:docker-ufw\nWhy is UFW not enough for Docker publishes?"}],"max_tokens":200}'
   ```
6. Point Continue / Open WebUI at `http://127.0.0.1:4000/v1`.

## Callbacks

Compose mounts teaching middleware from `reference/litellm/` (skill inject + Bronze + persona). Details: [docs/guides/wire-middleware.md](../docs/guides/wire-middleware.md).

## Harden before LAN exposure

- Keep publishes on `127.0.0.1` until you understand DOCKER-USER (`skills/docker-ufw`).
- Never put real master keys in git.
- Add your own backup/DR — this example has none.

## Next

- [docs/guides/eval-harness.md](../docs/guides/eval-harness.md) + `examples/harness/`
- [docs/guides/nightly-sentinel.md](../docs/guides/nightly-sentinel.md) + `examples/sentinel/`
- [docs/guides/model-challenge-wire-drop.md](../docs/guides/model-challenge-wire-drop.md)
