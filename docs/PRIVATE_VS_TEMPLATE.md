# Private lab vs this template

| Capability | This template | Typical private Alfred-like lab |
|------------|---------------|----------------------------------|
| Ollama + LiteLLM localhost | Yes | Yes |
| Skill inject (`#domain:` / phrases) | Yes (ops-core) | Larger personal registry |
| Coach this Prompt | Yes | Often core |
| Bronze compress | Yes (self → FIM) | Yes + optional vector DB tenants |
| MAX_LOADED=1 / KV q8_0 | Yes | Common on 12GB-class GPUs |
| Local websearch proxy | Off (`ALFRED_WEBSEARCH=0`) | Optional on a private Docker network |
| Applicability judge | Off | Optional LLM judge |
| Soft / deferred skills | Documented pattern | Lab-specific deferred cards |
| Spec Kit HITL loop | Docs only | Planner + one-task coder |
| Nightly digests / mail | Sanitized package under `examples/sentinel/` (env-driven; ICMP + optional controller NHS; secrets off-repo) | Live cron + private mailer / mounts |
| Host-tools modularity | Documented thin-launcher + `lib/` pattern in Sentinel SETUP | Larger private packages (eval weekly, model ops, …) |
| SoT sync | `scripts/sync-skills.sh` (restart) | Private git → ingest/reload helper |
| Personal IoT / host mounts | No | Yes |
| Disaster recovery / backups | No | Yes |

**Honesty:** this repo trails any live private lab on purpose. Copy rails, not
secrets. When you maintain private middleware twins, re-export a **sanitized**
subset into `middleware/` — never auto-publish `.env`, real LAN CIDRs, or
personal skills.
