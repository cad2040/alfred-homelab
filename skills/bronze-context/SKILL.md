---
name: bronze-context
description: >-
  Rolling Bronze chat compression before Ollama overflow. Per-alias budgets in
  bronze_budgets.yaml (≈0.61×num_ctx). Self-summarize first; FIM /api/generate
  fallback; extractive stub last. Optional Chroma bronze_context_log.
source_repo: cad2040/alfred-homelab
source_path: skills/bronze-context
primary_domain: bronze-context
domains: [bronze-context]
routing_tags: ["#domain:bronze-context"]
preferred_model: alfred-coder
---

# Bronze rolling context
#domain: bronze-context

## Hard rules
1. Specialist **`num_ctx`** comes from LiteLLM `config.yaml`. Hitting the wall can return an **empty** stream.
2. Middleware compresses when estimated tokens (messages **+ tools**) exceed that alias’s **`compress_threshold`** (≈ **0.61 × num_ctx**).
3. Summarizer order: **self** (resident alias) → FIM `/api/generate` → extractive stub. Never `/api/chat` on a base FIM tag.
4. Do **not** pin FIM with `keep_alive: -1` under `MAX_LOADED=1`.
5. Optional Chroma upsert is fire-and-forget (`CHROMA_URL`); chat must not block on it.
6. Blank replies after a long tool-heavy chat → treat as context overflow first.

## Locate
- Template: `middleware/alfred_middleware.py`
- Budgets: `deploy/compose/litellm/bronze_budgets.yaml`

## Never
Invent a second context system; blame “model confusion” before checking overflow; pin FIM permanently for Bronze.
