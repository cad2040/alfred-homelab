# Alfred Homelab — deploy template

**Sanitized deploy kit** for an Alfred-like local-LLM lab: Ollama + LiteLLM,
skill inject, Bronze compress, and a thin ops-core Gold set — including
**Coach this Prompt**.

This is **not** a clone of a private estate. No garden/IoT skills, no Sentinel
mail, no SearXNG, no DR. Rails first; weights second; **HITL co-pilot**, never
an unsupervised agent.

## Quick start

```bash
git clone https://github.com/cad2040/alfred-homelab.git
cd alfred-homelab
./scripts/bootstrap.sh    # .env + compose up + pull coder
# edit deploy/compose/.env → set LITELLM_MASTER_KEY
./scripts/smoke.sh        # DOCKER-USER inject + Coach phrase
```

Clients: `http://127.0.0.1:4000/v1` with `Authorization: Bearer $LITELLM_MASTER_KEY`.

CPU-only: `ALFRED_CPU=1 ./scripts/bootstrap.sh`

## What ships

| Area | Location |
|------|----------|
| Bootstrap / smoke / sync | [`scripts/`](scripts/) |
| Compose (MAX_LOADED=1) | [`deploy/compose/`](deploy/compose/) |
| Sanitized LiteLLM twins | [`middleware/`](middleware/) |
| Thin domains | [`routing/domains.yaml`](routing/domains.yaml) |
| Ops-core skills | [`skills/`](skills/) |
| Template vs private | [`docs/PRIVATE_VS_TEMPLATE.md`](docs/PRIVATE_VS_TEMPLATE.md) |
| Architecture / request flow | [`docs/architecture.md`](docs/architecture.md) |
| Security posture | [`docs/SECURITY.md`](docs/SECURITY.md) |
| Deeper learning path | [`docs/LEARNING_PATH.md`](docs/LEARNING_PATH.md) (after smoke) |
| Bring-up | [`deploy/HUMAN.md`](deploy/HUMAN.md) / [`deploy/agent/AGENTS.md`](deploy/agent/AGENTS.md) |

### Ops-core skills

`coach-this-prompt` · `docker-ufw` · `safe-script-production` · `vram-runtime` ·
`bronze-context` · `skill-gold-authoring`

### Product aims (co-pilot)

1. Monitor the lab safely  
2. Speed up development — Alfred drafts; **you** review  
3. Capture reusable fixes as Gold  
4. **Coach prompts** — reorder thoughts into agent-optimized messages  

## Private upgrades (not in this repo)

Soft-parked future skills, Spec Kit HITL full loop, Sentinel digests, SearXNG,
applicability judge, Chroma Gold ingest cron, estate IoT cards, DR/backups.
Optional depth (harness / Sentinel skeleton / challenge pattern) lives under
`docs/guides/` + `examples/`. See [docs/PRIVATE_VS_TEMPLATE.md](docs/PRIVATE_VS_TEMPLATE.md).

## License

MIT — see [LICENSE](LICENSE). Firewall and host scripts can break labs if
misapplied; read twice, HITL always.
