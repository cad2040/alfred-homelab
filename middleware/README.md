# Middleware (sanitized LiteLLM twins)

Live-shaped callbacks for the deploy template — **not** a byte copy of any
private estate.

| File | Role |
|------|------|
| `alfred_routing_callback.py` | Phrase / `#domain:` / keywords → skill inject |
| `alfred_middleware.py` | Bronze compress (self-summarize → FIM fallback) |
| `custom_prompt.py` | Optional persona (`ALFRED_PERSONA`, empty = off) |

**Defaults:** `ALFRED_WEBSEARCH=0`, `ALFRED_SKILL_JUDGE=0`. No SearXNG, no
`/mnt/alfred` hard fails, no stack-monitor.

Compose mounts this directory on LiteLLM `PYTHONPATH` (`/app/config`).
Wire-up: [docs/guides/wire-middleware.md](../docs/guides/wire-middleware.md).

When the private SoT twins change, re-export a sanitized subset here — do not
publish secrets or estate skills.
