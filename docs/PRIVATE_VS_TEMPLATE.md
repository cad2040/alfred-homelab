# Private estate vs this template

| Capability | This template | Typical private Alfred |
|------------|---------------|------------------------|
| Ollama + LiteLLM localhost | Yes | Yes |
| Skill inject (`#domain:` / phrases) | Yes (ops-core) | Large personal registry |
| Coach this Prompt | Yes | Yes (core) |
| Bronze compress | Yes (self → FIM) | Yes + Chroma tenants |
| MAX_LOADED=1 / KV q8_0 | Yes | Yes |
| SearXNG / `#websearch` | Off (`ALFRED_WEBSEARCH=0`) | Often on alfred-net |
| Applicability judge | Off | Optional LLM judge |
| Soft skills (`skills/_soft/`) | Documented pattern | Printer / voice / pools |
| Spec Kit HITL loop | Docs only | Planner + one-task coder |
| Sentinel / msmtp digests | Skeleton under `examples/` | Live cron + mail |
| SoT sync | `scripts/sync-skills.sh` (restart) | git push → `alfred-sync-skills` |
| Estate IoT / exo / mounts | No | Yes |
| DR / Stage backups | No | Yes |

**Honesty:** this repo trails a live private lab on purpose. Copy rails, not
secrets. When private middleware twins change, re-export a **sanitized** subset
into `middleware/` — never auto-publish `.env`, LAN CIDRs, or personal skills.
