# Alfred Homelab

**A how-to guide and sanitized extract** for building an Alfred-like local-LLM lab: aliases, Gold skills, Bronze context compression, eval harnesses, and a nightly Sentinel — without dumping a private estate.

Private estate repos stay private. This repo helps other homelab makers walk the same path: **rails first, weights second**.

## Start here

1. **[docs/LEARNING_PATH.md](docs/LEARNING_PATH.md)** — ordered journey (gateway → skills → Bronze → VRAM → challenge/wire → harness → Sentinel)
2. **[docs/architecture.md](docs/architecture.md)** — strengths, weaknesses, design principles
3. **[deploy/HUMAN.md](deploy/HUMAN.md)** / **[deploy/agent/AGENTS.md](deploy/agent/AGENTS.md)** — bring-up

## Quick start

```bash
git clone https://github.com/cad2040/alfred-homelab.git
cd alfred-homelab
cp deploy/compose/.env.example deploy/compose/.env
# set LITELLM_MASTER_KEY to a long random string

cd deploy/compose
# GPU:
docker compose up -d
# CPU-only:
# docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d

docker exec alfred-ollama-example ollama pull qwen2.5:7b-instruct
# optional Bronze summarizer (base tag):
# docker exec alfred-ollama-example ollama pull qwen2.5-coder:1.5b-base
```

Clients: `http://127.0.0.1:4000/v1` with your master key. Try a chat that includes `#domain:docker-ufw`.

## What this repo includes

| Area | Location |
|------|----------|
| Learning path | `docs/LEARNING_PATH.md` |
| Architecture (honest) | `docs/architecture.md` |
| Wire middleware | `docs/guides/wire-middleware.md` + `reference/litellm/` |
| Bronze budgets | `docs/guides/bronze-budgets.md` |
| Model challenge / wire / drop | `docs/guides/model-challenge-wire-drop.md` |
| Eval harness | `docs/guides/eval-harness.md` + `examples/harness/` |
| Nightly Sentinel | `docs/guides/nightly-sentinel.md` + `examples/sentinel/` |
| Example Gold skills | `skills/` |
| Example Compose | `deploy/compose/` (callbacks mounted) |

### Example Compose scope (be precise)

**Included:** Ollama + LiteLLM on localhost, teaching **skill inject**, **Bronze** middleware, persona, sample skills, budgets.

**Not included:** full private router (SearXNG, applicability judge, deny lists), DR/backups, SMTP digests, production challenge CLIs, Open WebUI. Those are documented as patterns to grow privately.

## Example Gold skills

- `docker-ufw` — DOCKER-USER vs UFW
- `safe-script-production` — dry-run / CONFIRM mutators
- `disk-usage` — path fidelity + dupe shortlists
- `bronze-context` / `vram-runtime` / `skill-gold-authoring`

## Relationship to a private estate

| This public repo | Your private estate |
|------------------|---------------------|
| How-to + sanitized reference code | Live domains, digests, DR, personal skills |
| Minimal Compose + teaching callbacks | Production compose, secrets, host paths |
| Example harness / Sentinel skeleton | Full matrices, cron, mail |

## License

MIT — see [LICENSE](LICENSE). Skills and firewall examples can break hosts if misapplied; read twice, HITL always.
