# Wire LiteLLM middleware (teaching extract)

This repo ships **sanitized** callbacks under [`reference/litellm/`](../../reference/litellm/):

| Module | Role |
|--------|------|
| `alfred_routing_skills.py` | `#domain:` / phrase → inject `SKILL.md` |
| `alfred_middleware_bronze.py` | Bronze rolling compress + optional Chroma |
| `custom_prompt.py` | Optional persona prepend |

They are intentionally smaller than a full private-estate fork (no unsupervised lanes, no SearXNG, no estate paths).

## Compose (already wired in the example)

`deploy/compose/docker-compose.yml` bind-mounts the three modules into `/app/config/` and sets:

```text
PYTHONPATH=/app/config
ALFRED_SKILLS_ROOT=/app/skills
ALFRED_DOMAINS_YAML=/app/config/domains.yaml
ALFRED_BRONZE_BUDGETS=/app/config/bronze_budgets.yaml
```

`config.yaml` registers:

```yaml
litellm_settings:
  callbacks:
    - alfred_routing_skills.proxy_handler_instance
    - alfred_middleware_bronze.proxy_handler_instance
    - custom_prompt.prompt_management
```

Recreate LiteLLM after edits:

```bash
cd deploy/compose && docker compose up -d --force-recreate litellm
```

## Manual install into an existing LiteLLM

1. Copy the three `.py` files next to your `config.yaml` (must be on `PYTHONPATH`).
2. Copy or bind your Gold `skills/` tree; set `ALFRED_SKILLS_ROOT`.
3. Add `bronze_budgets.yaml` + optional `domains.yaml`.
4. Append the three callback entries; recreate the container.
5. Smoke: chat with `#domain:docker-ufw` and a long thread (Bronze).

## Order of hooks

LiteLLM runs callbacks in list order. Recommended:

1. **Routing / skill inject** — policy before compress
2. **Bronze** — may drop middle turns
3. **Persona** — last (or skip on planner/security)

## Environment knobs

| Env | Default | Meaning |
|-----|---------|---------|
| `ALFRED_MAX_SKILL_CHARS` | `4500` | Inject budget for SKILL.md bodies |
| `ALFRED_BRONZE_CTX_RATIO` | `0.61` | threshold ≈ ratio × num_ctx |
| `ALFRED_FIM_TAG` | `qwen2.5-coder:1.5b-base` | `/api/generate` summarizer |
| `CHROMA_URL` | empty | If set, best-effort Bronze upsert |
| `OLLAMA_HOST` | `http://ollama:11434` | Direct Ollama (no LiteLLM re-entry) |

## Hardening notes

- Never commit real master keys.
- Callbacks call Ollama **directly** for summarize/embed — avoid re-entering LiteLLM hooks.
- If FIM tag is missing, Bronze falls back to extractive stubs (still protects num_ctx).
- Private labs often add: websearch inject, applicability scoring, deny-tool lists, twin `*-fc` aliases — port those carefully; don’t paste estate secrets into a public fork.
