# Model challenge → wire → drop

Pattern for trying a new Ollama tag against a live LiteLLM **alias** without hand-editing production blindly.

## Flow

```text
pull candidate → A/B harness vs current alias → judge summary
        │
        ├─ clear win + acceptable ctx  →  wire (+ smoke; rollback on fail)
        └─ tie / lose / bad ctx trade  →  drop weights + temp aliases
```

## Rules of thumb

1. **Pull first** (or let automation pull). Weights must exist in Ollama before LiteLLM points at them.
2. Register a **temporary candidate alias** for the A/B; do not overwrite production until smoke passes.
3. Print a human **SUMMARY** (pass rates, per-challenge, judge recommendation).
4. Prefer **baseline when pass rates tie**. A smaller `num_ctx` (e.g. 8k replacing 32k) is a real regression.
5. Wire must update **Bronze compress thresholds** when `num_ctx` changes (~0.61 × ctx).
6. Smoke failure → **automatic rollback** of config (+ budgets).
7. Drop removes Ollama tags that are **not** still referenced by an alias; clean challenge report dirs so digests do not bloat.

## Example CLI shape (names may differ in your lab)

```bash
# Challenge
alfred-model-challenge --tag gemma2:9b --alias alfred-reasoner \
  --style openai --num-ctx 8192

# Wire only if SUMMARY says wire_candidate and you accept the ctx trade
alfred-model-wire --tag gemma2:9b --alias alfred-reasoner \
  --style openai --num-ctx 8192 --yes

# Discard experiment
alfred-model-drop --tag gemma2:9b --yes
```

Backend style:

- `openai/*` + `http://ollama:11434/v1` — instruct chat / tools
- `ollama/*` + `think: false` — thinking models that otherwise burn tokens on CoT

## What “good” looks like after drop

- Tag absent from `ollama list`
- No temp candidate in LiteLLM config / `/v1/models`
- Production aliases unchanged
- Challenge report dirs for that tag removed
