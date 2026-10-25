# Alfred Homelab

**A how-to guide and sanitized extract** for building an Alfred-like local-LLM lab: aliases, Gold skills, Bronze context compression, eval harnesses, and a nightly Sentinel — without dumping a private estate.

Private estate repos stay private. This repo helps other homelab makers walk the same path: **rails first, weights second**.

It is a **teaching subset**, not a drop-in clone of any live lab. Pattern guides often describe private CLIs/jobs that are **not** in this tree — each guide says so up front.

## Start here

1. **[docs/LEARNING_PATH.md](docs/LEARNING_PATH.md)** — ordered journey (gateway → skills → Bronze → VRAM → challenge/wire → harness → Sentinel → memory tiers)
2. **[docs/architecture.md](docs/architecture.md)** — tradeoffs + what ships vs private extras
3. **[deploy/HUMAN.md](deploy/HUMAN.md)** / **[deploy/agent/AGENTS.md](deploy/agent/AGENTS.md)** — bring-up

## Quick start

```bash
git clone https://github.com/cad2040/alfred-homelab.git   # or your fork URL
cd alfred-homelab
cp deploy/compose/.env.example deploy/compose/.env
# set LITELLM_MASTER_KEY to a long random string

cd deploy/compose
# GPU:
docker compose up -d
# CPU-only (if Docker still errors on nvidia reservations, see HUMAN.md):
# docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d

docker exec alfred-ollama-example ollama pull qwen2.5:7b-instruct
# optional Bronze summarizer (base tag) — without it, Bronze uses extractive stubs:
# docker exec alfred-ollama-example ollama pull qwen2.5-coder:1.5b-base
```

Clients: `http://127.0.0.1:4000/v1` with your master key. Try a chat that includes `#domain:docker-ufw`.

Smoke steps: [deploy/HUMAN.md](deploy/HUMAN.md). Compose was written against LiteLLM `v1.81.0-stable` + current Ollama; **re-verify** on your host after first `up` (callback APIs drift).

## What this repo includes

| Area | Location | Honesty |
|------|----------|---------|
| Learning path | `docs/LEARNING_PATH.md` | |
| Architecture | `docs/architecture.md` | Tradeoffs; no community rankings |
| Wire middleware | `docs/guides/wire-middleware.md` + `reference/litellm/` | Skill inject + Bronze + optional persona |
| Bronze budgets | `docs/guides/bronze-budgets.md` | |
| Model challenge / wire / drop | `docs/guides/model-challenge-wire-drop.md` | **Pattern only** — CLIs private |
| Eval harness | `docs/guides/eval-harness.md` + `examples/harness/` | **Keyword toy** |
| Nightly Sentinel | `docs/guides/nightly-sentinel.md` + `examples/sentinel/` | Digest **skeleton** |
| Memory tiers / prune | `docs/guides/memory-tiers-curation.md` + `examples/curation/` | **Gates + demo**; prune cron private |
| Example Gold skills | `skills/` | |
| Example Compose | `deploy/compose/` | Callbacks mounted |

### Example Compose scope (be precise)

**Included:** Ollama + LiteLLM on localhost, teaching **skill inject**, **Bronze** middleware, optional persona, sample skills, budgets.

**Not included:** full private router (SearXNG, applicability judge, deny lists), DR/backups, SMTP digests, production challenge CLIs, Open WebUI, nightly Chroma prune. Those are documented as patterns to grow privately.

Optional persona: set `ALFRED_PERSONA=` empty or drop `custom_prompt` from `config.yaml` callbacks.

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
| Example harness / Sentinel skeleton | Full matrices, cron, mail, prune |

## License

MIT — see [LICENSE](LICENSE). Skills and firewall examples can break hosts if misapplied; read twice, HITL always.
