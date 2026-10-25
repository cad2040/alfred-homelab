# Reference LiteLLM callbacks (sanitized)

Teaching extracts — not a byte-for-byte copy of any private estate.

| File | Purpose |
|------|---------|
| `alfred_routing_skills.py` | `#domain:` / phrases → Gold skill inject (no applicability judge) |
| `alfred_middleware_bronze.py` | Bronze compress + optional Chroma upsert (no prune) |
| `custom_prompt.py` | Optional persona (`ALFRED_PERSONA=` to disable) |

Wire-up: [docs/guides/wire-middleware.md](../../docs/guides/wire-middleware.md).

Re-smoke after LiteLLM image upgrades — callback registration can drift.
