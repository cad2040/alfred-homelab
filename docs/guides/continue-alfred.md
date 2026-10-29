# Continue + Alfred (smooth Spec Kit / Agent use)

Practical Continue.dev setup for this template’s LiteLLM aliases. Complements
[deploy/HUMAN.md](../../deploy/HUMAN.md) and [architecture.md](../architecture.md).

## Point Continue at the gateway

After `./scripts/smoke.sh`:

- **API base:** `http://127.0.0.1:4000/v1` (or your LAN LiteLLM bind if you intentionally exposed it)
- **Key:** `LITELLM_MASTER_KEY` from `deploy/compose/.env` (never commit it)
- **Aliases:** `alfred-coder`, `alfred-reasoner`, `alfred-technical-planner`, `alfred-security`

Prefer aliases over raw Ollama tags so Modelfile `num_ctx` and SYSTEM prompts apply.

## Per-model context in `~/.continue/config.yaml`

Continue’s `maxTokens` is **output** size, not the model window. Set **`contextLength`**
to match each Modelfile / LiteLLM alias or Continue may compact early and truncate edits.

Reference map (12GB-class template defaults):

| Continue model name | LiteLLM / Ollama alias | `contextLength` | Suggested `maxTokens` |
|---------------------|------------------------|-----------------|------------------------|
| Alfred Coder | `alfred-coder` | **16000** | 4096 |
| Alfred Reasoner | `alfred-reasoner` | **32000** | 8192 |
| Alfred Technical Planner | `alfred-technical-planner` | **32000** | 8192 |

Example fragment:

```yaml
  - name: Alfred Coder
    provider: openai
    model: alfred-coder
    apiBase: http://127.0.0.1:4000/v1
    # apiKey via env / local secrets — do not commit
    defaultCompletionOptions:
      contextLength: 16000
      maxTokens: 4096

  - name: Alfred Reasoner
    provider: openai
    model: alfred-reasoner
    apiBase: http://127.0.0.1:4000/v1
    roles: [chat, summarize]
    defaultCompletionOptions:
      contextLength: 32000
      maxTokens: 8192

  - name: Alfred Technical Planner
    provider: openai
    model: alfred-technical-planner
    apiBase: http://127.0.0.1:4000/v1
    capabilities: [tool_use]
    defaultCompletionOptions:
      contextLength: 32000
      maxTokens: 8192
```

Reload Continue (or the IDE window) after changing `config.yaml`.

## Role split (HITL)

| Job | Model | Mode |
|-----|--------|------|
| Spec Kit docs (`spec` / `plan` / `tasks` / analyze) | **Alfred Technical Planner** | Agent + edit tools |
| Chat / critique / summarize | **Alfred Reasoner** | Chat (often no tools on LiteLLM) |
| Code / firmware / scripts | **Alfred Coder** | Agent + edit tools, **one task per turn** |
| Security digest | **Alfred Security** | Chat |

Planner drafts Spec Kit markdown with edit tools; human reviews; coder implements **one** Alfred-sized task. Do not ask Reasoner to write files in Agent mode if tools are stripped on the gateway.

**Apply vs chat ACK:** `edit_existing_file` can report “Successfully edited” while Apply leaves an empty section. Planner config drops the `apply` role (Coder/Flash apply). After edits Alfred must `read_file` verify. Accept diffs only when the body is present; for small docs prefer full-file `changes`.

## Spec Kit in Continue (not Cline)

Cline-style installs tend to bloat context. Prefer Spec Kit’s **`generic`** integration writing into the project’s Continue prompts.

### Global estate preset (every new / existing repo)

Hard-wires live in the estate preset (not only GardenSensors):

`C:\Code\digital_estate_context\presets\alfred-continue-speckit`

| Command | Wrap behavior |
|---------|----------------|
| `/speckit.analyze` | Continue `invokable` frontmatter, Windows `powershell -File`, adversarial bar |
| `/speckit.implement` | Continue `invokable` frontmatter, **one task per chat** then stop + new-chat banner |

**New repo** (`specify init --preset` accepts catalog IDs only — not a local `--dev` path — so add + stamp right after init):

```powershell
specify init --here --force --non-interactive `
  --integration generic `
  --integration-options="--commands-dir .continue/prompts" `
  --script ps

specify preset add --dev C:\Code\digital_estate_context\presets\alfred-continue-speckit --priority 5

powershell -NoProfile -ExecutionPolicy Bypass -File `
  C:\Code\digital_estate_context\presets\alfred-continue-speckit\scripts\stamp-continue-prompts.ps1
```

**Existing Spec Kit project:**

```powershell
specify integration uninstall cline --force   # if present / broken
specify integration install generic `
  --integration-options="--commands-dir .continue/prompts" `
  --force --script ps

specify preset add --dev C:\Code\digital_estate_context\presets\alfred-continue-speckit --priority 5

powershell -NoProfile -ExecutionPolicy Bypass -File `
  C:\Code\digital_estate_context\presets\alfred-continue-speckit\scripts\stamp-continue-prompts.ps1
```

The stamp step is required for Continue: Spec Kit’s **generic** integration has no
agent registrar, so composed wraps stay under `.specify/presets/.../.composed/`
until copied into `.continue/prompts/`.

After `specify integration upgrade --force`, re-run `preset add --dev` + stamp.

Optional later: publish a ZIP + user catalog entry so `specify init --preset alfred-continue-speckit` works without `--dev`. Until then, `--dev` + stamp is the SoT.

Commit `.continue/prompts/` with the project. Keep `.specify/` local/tooling as you prefer; feature docs live under `specs/`.

**Invoke:** type `/` in Continue chat and pick `/speckit.analyze` (dot separator with `generic`).  
**Do not** stack `#domain:…` tags on Spec Kit workflow commands — domains are for implementation slices only.

Active feature: `.specify/feature.json` → `feature_directory` (not “whatever branch you’re on”).

## Windows shell pitfalls

On hosts with Windows PowerShell 5.x (no `pwsh`):

- Use `powershell -NoProfile -ExecutionPolicy Bypass -File .specify/scripts/powershell/<script>.ps1 …`
- **Do not** use `pwsh`
- **Do not** chain with `&&` (invalid in Windows PowerShell 5); use `;` or separate commands

Bake that into Spec Kit prompts if agents keep inventing `pwsh` / `&&`.

## Context compaction (why full-file edits go wrong)

When chat + tool traces near the budget, Continue **compacts** history (often via a model with the `summarize` role). Summaries keep *intent*, not full markdown bodies. After a “summarize” blip, agents may rewrite a long `plan.md` from a skeleton and look like they “deleted half the doc.”

**UI note:** Continue may show **“Generating conversation summary”** / **Compact conversation** in the chat panel. That is **Continue’s own history compaction**, not Alfred **Bronze** context. Bronze injects durable lab notes; Compact conversation rewrites *this thread’s* memory so the next turn fits.

Mitigations:

- One Spec Kit artifact per chat after analyze (`plan.md` only, then new chat for `tasks.md`)
- Prefer surgical “replace this section” edits over whole-file rewrites
- If summarize fires mid-edit: reject full-file apply; `@`-reattach the file and patch
- Keep analyze / remediate / implement in separate sessions

## Implement: one task per chat

The estate preset wraps `/speckit.implement` for **one Alfred-sized task per
Continue chat**, then stops with a “clear context / new chat” banner. Agents
cannot wipe history themselves; a new chat is the compaction safeguard.
Override only with explicit `MULTI_TASK=1` in the slash args. Prefer:
`/speckit.implement T006` → HITL → new chat → next id.

## Analyze: stay adversarial

Soft “looks complete, start implementing” reports are a failure mode. The
estate preset’s adversarial bar covers auth/contract gaps, FR→task coverage,
SHOULD vs MUST, orphan edge cases, and constitution MUST. Require findings
tables; no rubber-stamp.

## Bronze context

If Bronze notes inject prior analyze results, they can **replay stale triage**
(e.g. “merge FR-007/008”). After a human triage, pin a short superseding note in
chat or update Bronze so the agent does not re-propose rejected merges.

## Quick checklist

- [ ] Smoke green; Continue aimed at LiteLLM `/v1`
- [ ] `contextLength` set per alias (16k coder / 32k reasoner+planner)
- [ ] Spec Kit prompts under `.continue/prompts/` with `invokable: true`
- [ ] Estate preset installed (`alfred-continue-speckit`) + Continue prompts stamped
- [ ] `/speckit.*` appears in Continue `/` menu
- [ ] Planner for Spec Kit docs; coder for one implementation task
- [ ] Windows: `powershell -File`, no `pwsh` / `&&`
- [ ] Watch for compaction mid-edit; one file per session when docs are large
