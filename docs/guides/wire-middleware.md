# Wire middleware (template twins)

Compose mounts [`middleware/`](../../middleware/) into the LiteLLM container as
`/app/config/*.py` with `PYTHONPATH=/app/config`.

## Callbacks (`config.yaml`)

```yaml
litellm_settings:
  callbacks:
    - alfred_routing_callback.proxy_handler_instance
    - alfred_middleware.proxy_handler_instance
    - custom_prompt.prompt_management
```

Order: **route/inject → Bronze → optional persona**.

## Important env

| Env | Default | Meaning |
|-----|---------|---------|
| `ALFRED_SKILLS_ROOT` | `/app/skills` | Gold skill dirs |
| `ALFRED_DOMAINS_YAML` | `/app/config/domains.yaml` | Thin registry |
| `ALFRED_MAX_SKILL_CHARS` | `4500` | Hard inject budget |
| `ALFRED_SKILL_CARDS_CHARS` | `3000` | Soft card catalog |
| `ALFRED_WEBSEARCH` | `0` | SearXNG off in template |
| `ALFRED_SKILL_JUDGE` | `0` | No LLM applicability judge |
| `ALFRED_PERSONA` | empty | Persona off |
| `ALFRED_CODER_TAG` / `_REASONER_TAG` / `_FIM_TAG` | see `.env.example` | Bronze self-summarize targets |

## Soft vs hard inject

- **Hard** (full `SKILL.md`): phrase triggers (e.g. `Coach this Prompt:`) or explicit non-umbrella `#domain:`.
- **Soft** (keyword / fallback): short skill **cards**; model may `#load_skill <id>`.

## After edits

```bash
./scripts/sync-skills.sh
./scripts/smoke.sh
```

## Re-verify on LiteLLM upgrades

Callback import paths drift. If logs show import errors, check volume mounts and
`PYTHONPATH`. Pin the Compose image tag you smoke-tested.

## Private upgrades

Local websearch proxies, extra host tools, and applicability judges live in
private labs — not this template. See
[PRIVATE_VS_TEMPLATE.md](../PRIVATE_VS_TEMPLATE.md).
