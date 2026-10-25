# Alfred Homelab

**A curated, public extract of patterns from a real local-LLM estate OS** — not a dump of someone’s private lab.

Alfred is how one builder runs **Ollama + LiteLLM + skills + eval** on a single GPU box (RTX 3060-class) without pretending a 7B/9B is Claude. The product is the **rails**: aliases, Gold skills, Bronze context compression, fail-closed host ops, and measured trust.

> Private estate repo stays private. This repo shares **reusable architecture, guides, deploy starters, and example Gold skills** for other homelab makers and agents.

## What you get

| Area | Contents |
|------|----------|
| Architecture | Strengths, weaknesses, and how pieces fit |
| Deploy | Example Compose + human & agent quickstarts |
| Guides | Model challenge/wire mindset, Bronze budgets, skill authoring |
| Example Gold skills | Sanitized, transferable cards (Docker/UFW, safe scripts, disk hunts, …) |

## Quick start (human)

```bash
git clone https://github.com/cad2040/alfred-homelab.git
cd alfred-homelab
cp deploy/compose/.env.example deploy/compose/.env
# edit .env — set LITELLM_MASTER_KEY to a long random string
cd deploy/compose && docker compose up -d
```

Point Continue / Open WebUI / any OpenAI client at `http://127.0.0.1:4000/v1` with that key. See [deploy/HUMAN.md](deploy/HUMAN.md).

## Quick start (AI agent)

Agents: read [deploy/agent/AGENTS.md](deploy/agent/AGENTS.md) first, then apply Compose from `deploy/compose/` without inventing secrets or publishing Ollama on `0.0.0.0`.

## Architecture (one screen)

```text
Clients (Continue, Open WebUI, scripts)
        │  OpenAI-compatible
        ▼
   LiteLLM aliases  ── routing / Bronze compress / persona
        │
        ▼
   Ollama (slot-1 FIM pin + slot-2 specialist hot-swap)
        │
        ├── Gold skills (domain cards injected by routing)
        └── Eval harness (optional — trust bands, not auto-promote)
```

Deep dive: [docs/architecture.md](docs/architecture.md).

## Example Gold skills

Under [`skills/`](skills/):

- `docker-ufw` — DOCKER-USER vs UFW; bind localhost for inference DBs
- `safe-script-production` — dry-run / CONFIRM gates for mutating scripts
- `disk-usage` — path fidelity + capacity/dupe shortlists (no inventing mounts)
- `skill-gold-authoring` — how to write a Gold card
- `bronze-context` — when/why rolling summarize before ctx overflow
- `vram-runtime` — FIM pin + specialist hot-swap mental model

Copy into your own skill registry; adapt domain IDs and paths to **your** lab.

## Relationship to a private estate

| This public repo | Your private estate |
|------------------|---------------------|
| Patterns & examples | Live `domains.yaml`, digests, DR, personal skills |
| Generic `/srv/alfred` paths | Your mounts / hostnames |
| Example Compose | Production compose + secrets |

Do **not** publish your private estate SoT. Curate outward; keep the messy truth inward.

## License

MIT — see [LICENSE](LICENSE). Skills retain practical “never” rules; adapt at your own risk on production hosts.

## Status

Living extract. APIs and script names may lag a private lab; treat this as **patterns + starting points**, not a turnkey appliance.
