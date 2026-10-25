# Bronze budgets (rolling context)

Local specialists have a hard `num_ctx`. When chat + tool schemas grow past a **compress threshold**, middleware should summarize the middle (systems + summary + last N turns) instead of sending an oversize request that returns empty.

## Default ratio

```text
compress_threshold ≈ max(2048, floor(0.61 × num_ctx))
```

Examples:

| `num_ctx` | ≈ threshold |
|-----------|-------------|
| 8192 | ~5k |
| 16384 | ~10k |
| 32768 | ~20k |

Keep a sidecar file (example: `bronze_budgets.yaml`) mapping each alias → `{num_ctx, compress_threshold}` and update it whenever you rewire context. Middleware should prefer that file, then fall back to reading `num_ctx` from LiteLLM `config.yaml`.

## Summarizer tips

- Prefer a **pinned small FIM/base** model via `/api/generate` for summaries (not `/api/chat` on base tags — they continue the transcript).
- Planner aliases may self-summarize at their own `num_ctx`.
- On summarize failure while over threshold: hard-drop the middle with a stub so the specialist still fits.

## Homelab lesson

Thresholds that stay at “20k forever” while you wire an 8k model will look like “the model is dumb” when the real bug is **overflow**. Budgets must follow the alias.
