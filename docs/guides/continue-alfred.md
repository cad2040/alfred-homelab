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
| Alfred Coder | `alfred-coder` | **16000** | **2048** (not 4096 — see compaction note) |
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
      maxTokens: 2048

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

**Apply vs chat ACK:** `edit_existing_file` can report “Successfully edited” while Apply leaves an empty section. Planner and Coder drop the `apply` role; **Gemini Flash** owns `apply`. After edits Alfred must `read_file` verify. Accept diffs only when the body is present; for small docs prefer full-file `changes` or `single_find_and_replace`.

**Windows path trap (red-X “does not exist”):** `read_file` accepts `C:\Code\…` absolutes; `edit_existing_file` / `create_new_file` / `single_find_and_replace` often fail with “does not exist” on those same paths. Always pass **workspace-relative** paths with forward slashes (`specs/011-…/tasks.md`). Check Continue → Models → **Apply** is Gemini Flash.

**Empty turn after Select-String:** alfred-coder sometimes returns **zero tool_calls + empty content** after a successful search, which ends the Agent loop with the checkbox still `[ ]`. Estate `/speckit.implement` forbids that; coder `baseAgentSystemMessage` requires another tool_call until `- [X]` mark. If it still stalls, nudge once with “emit work + single_find_and_replace mark tool_calls now” — do not trust compaction summaries.

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

powershell -NoProfile -ExecutionPolicy Bypass -File `
  C:\Code\digital_estate_context\presets\alfred-continue-speckit\scripts\apply-to-project.ps1
```

(`apply-to-project.ps1` = `specify preset add --dev` + stamp. Prefer this over calling
stamp alone so every new repo gets the latest slim implement / tool-name fixes.)

**Existing Spec Kit project:**

```powershell
specify integration uninstall cline --force   # if present / broken
specify integration install generic `
  --integration-options="--commands-dir .continue/prompts" `
  --force --script ps

powershell -NoProfile -ExecutionPolicy Bypass -File `
  C:\Code\digital_estate_context\presets\alfred-continue-speckit\scripts\apply-to-project.ps1
```

Spec Kit’s **generic** integration has no agent registrar, so wraps must be stamped
into `.continue/prompts/`. After `specify integration upgrade --force`, or after
pulling estate Continue fixes, re-run **apply-to-project.ps1**.

Optional later: publish a ZIP + user catalog entry so `specify init --preset alfred-continue-speckit` works without `--dev`. Until then, `--dev` + stamp is the SoT.

Commit `.continue/prompts/` with the project. Keep `.specify/` local/tooling as you prefer; feature docs live under `specs/`.

**Invoke:** type `/` in Continue chat and pick `/speckit.analyze` (dot separator with `generic`).  
**Do not** stack `#domain:…` tags on Spec Kit workflow commands — domains are for implementation slices only.

Active feature: `.specify/feature.json` → `feature_directory` (not “whatever branch you’re on”).

## Windows shell pitfalls

Continue’s Agent tool is **`run_terminal_command`**. There is no tool named `powershell`.
Put the OS command *inside* that tool’s `command` argument.

On hosts with Windows PowerShell 5.x (no `pwsh`):

- Use `powershell -NoProfile -ExecutionPolicy Bypass -File .specify/scripts/powershell/<script>.ps1 …`
- **Do not** use `pwsh`
- **Do not** chain with `&&` (invalid in Windows PowerShell 5); use `;` or separate commands

If Alfred emits **Invalid Tool Call / Tool powershell not found**, it invented a tool name — retry with `run_terminal_command`.

## Context compaction (why full-file edits go wrong)

Continue auto-compacts near
`contextLength − maxTokens − buffer` (buffer ≈ `maxTokens` up to 15k) — **not** at the full window.
On coder **16k / maxTokens 4096** that threshold is ~**7.8k** tokens, so a slash prompt + tool schemas + one `tasks.md` read already fires **Generating conversation summary**. Prefer **maxTokens: 2048** on Alfred Coder (~11k headroom) and keep `/speckit.implement` ultra-slim (no full `tasks.md` read; skip prereq when `feature.json` exists).

When chat + tool traces near that threshold, Continue **compacts** history (often via a model with the `summarize` role). Summaries keep *intent*, not full markdown bodies. After a “summarize” blip, agents may rewrite a long `plan.md` from a skeleton and look like they “deleted half the doc.”

**UI note:** Continue may show **“Generating conversation summary”** / **Compact conversation** in the chat panel. That is **Continue’s own history compaction**, not Alfred **Bronze** context. Bronze injects durable lab notes; Compact conversation rewrites *this thread’s* memory so the next turn fits.

Mitigations:

- One Spec Kit artifact per chat after analyze (`plan.md` only, then new chat for `tasks.md`)
- Prefer surgical “replace this section” edits over whole-file rewrites
- If summarize fires mid-edit: reject full-file apply; `@`-reattach the file and patch
- Keep analyze / remediate / implement in separate sessions

## Implement: one task per chat

The estate preset stamps a **slim** `/speckit.implement` (no upstream multi-phase
CORE template — that ~15KB blob compacted 16k `alfred-coder` before any edit).
One Alfred-sized task per Continue chat, then a “clear context / new chat” banner.
Agents cannot wipe history themselves; a new chat is the compaction safeguard.
Override only with explicit `MULTI_TASK=1` in the slash args. Prefer:
`/speckit.implement T006` → HITL → new chat → next id. After preset updates,
re-run the stamp script and **reload Continue**.

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
