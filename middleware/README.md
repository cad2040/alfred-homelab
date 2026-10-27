# Middleware (sanitized LiteLLM twins)

Teaching callbacks for the deploy template — **not** a dump of any private lab.

| File | Role |
|------|------|
| `alfred_routing_callback.py` | Phrase / `#domain:` / keywords → skill inject |
| `alfred_middleware.py` | Bronze compress (self-summarize → FIM fallback) |
| `custom_prompt.py` | Optional persona (`ALFRED_PERSONA`, empty = off) |

**Defaults:** `ALFRED_WEBSEARCH=0`, `ALFRED_SKILL_JUDGE=0`. No websearch backend,
no host-absolute path hard-fails, no stack-monitor.

Compose mounts this directory on LiteLLM `PYTHONPATH` (`/app/config`).
Wire-up: [docs/guides/wire-middleware.md](../docs/guides/wire-middleware.md).

When your private twins change, re-export a sanitized subset here — do not
publish secrets or personal skills.
