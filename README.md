# Alfred Homelab — deploy template

**Sanitized deploy kit** for an Alfred-like local-LLM lab: Ollama + LiteLLM,
skill inject, Bronze compress, and a thin ops-core Gold set — including
**Coach this Prompt**.

This is **not** a clone of any private lab. No personal IoT skills, no digest
mail, no websearch proxy, no DR. Rails first; weights second; **HITL co-pilot**,
never an unsupervised agent.

## Quick start

```bash
git clone https://github.com/cad2040/alfred-homelab.git
cd alfred-homelab
./scripts/bootstrap.sh    # .env + compose up + pull bases + Modelfiles
# edit deploy/compose/.env → set LITELLM_MASTER_KEY
./scripts/smoke.sh        # DOCKER-USER inject + Coach phrase
```

Clients: `http://127.0.0.1:4000/v1` with `Authorization: Bearer $LITELLM_MASTER_KEY`.

CPU-only: `ALFRED_CPU=1 ./scripts/bootstrap.sh` — bring-up only; 14B/9B on CPU
is painfully slow. Prefer GPU for real use.

**Weights:** day-1 defaults are a **12GB-class reference map** (coder 14B Q3 @16k,
reasoner/planner qwen3.5:9b @32k, Foundation-Sec @16k, FIM optional). See
[docs/architecture.md](docs/architecture.md). Pulls are large — plan disk.

**Smoke:** needs `curl`. `python3` or `jq` optional (pretty-print only). Set a
real `LITELLM_MASTER_KEY` before `./scripts/smoke.sh`.

## What ships

| Area | Location |
|------|----------|
| Bootstrap / smoke / sync | [`scripts/`](scripts/) |
| Compose (`MAX_LOADED=1`) | [`deploy/compose/`](deploy/compose/) |
| Ollama Modelfiles | [`deploy/modelfiles/`](deploy/modelfiles/) |
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

### What it’s for (co-pilot)

1. Safer lab monitoring habits  
2. Faster drafts — Alfred proposes; **you** review  
3. Saving reusable fixes as Gold skills  
4. Coaching rough notes into clearer prompts  

## Private upgrades (not in this repo)

Deferred personal skills, Spec Kit HITL full loop, nightly digests, local
websearch, applicability judge, vector Gold ingest, IoT cards, DR/backups.
Optional depth (harness / Sentinel skeleton / challenge pattern) lives under
`docs/guides/` + `examples/`. See [docs/PRIVATE_VS_TEMPLATE.md](docs/PRIVATE_VS_TEMPLATE.md).

## License

MIT — see [LICENSE](LICENSE). Firewall and host scripts can break labs if
misapplied; read twice, HITL always.
