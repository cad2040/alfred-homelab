---
name: bronze-context
description: >-
  Rolling context compression before specialist num_ctx overflow. Threshold
  ≈0.61×num_ctx per alias; small FIM/base summarizer via /api/generate when possible.
primary_domain: bronze-context
domains: [bronze-context]
routing_tags: ["#domain:bronze-context"]
preferred_model: alfred-coder
---

# Bronze rolling context
#domain: bronze-context

## Hard rules

1. Each chat alias has a **`num_ctx`**. Overflow can truncate or return **empty** streams in UIs.
2. Compress when estimated tokens (messages **+ tool schemas**) exceed that alias’s **`compress_threshold`** (≈ **0.61 × num_ctx**; keep a `bronze_budgets.yaml`).
3. Summarizer: prefer a pinned small **base** model via Ollama **`/api/generate`** — **never** `/api/chat` on base tags (they continue the transcript).
4. On unusable summary: extractive stub still allowed — keep systems + summary + last few turns.
5. Blank replies after long tool-heavy chats → treat as **context overflow** first.

## Never

Leave thresholds at “20k forever” after wiring an 8k model; use chat APIs on base FIM tags for summaries.
