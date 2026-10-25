# Human deploy (example stack)

## Requirements

- Docker + Compose
- NVIDIA Container Toolkit (or edit Compose to drop the GPU block for CPU experiments)
- Disk for model weights

## Steps

1. Clone this repo.
2. `cp deploy/compose/.env.example deploy/compose/.env` and set `LITELLM_MASTER_KEY`.
3. `cd deploy/compose && docker compose up -d`
4. Pull a chat model:
   ```bash
   docker exec alfred-ollama-example ollama pull qwen2.5:7b-instruct
   ```
5. Smoke:
   ```bash
   curl -s http://127.0.0.1:4000/v1/models \
     -H "Authorization: Bearer $LITELLM_MASTER_KEY" | head
   curl -s http://127.0.0.1:4000/v1/chat/completions \
     -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"alfred-coder","messages":[{"role":"user","content":"ping"}],"max_tokens":32}'
   ```
6. Point Continue / Open WebUI / scripts at `http://127.0.0.1:4000/v1`.

## Harden before LAN exposure

- Keep publishes on `127.0.0.1` until you understand DOCKER-USER (see `skills/docker-ufw`).
- Never put real master keys in git.
- Add your own backup/DR — this example has none.

## Next

- Read [docs/architecture.md](../docs/architecture.md)
- Copy example Gold skills into your router / skill store
- When swapping models, follow [docs/guides/model-challenge-wire-drop.md](../docs/guides/model-challenge-wire-drop.md)
