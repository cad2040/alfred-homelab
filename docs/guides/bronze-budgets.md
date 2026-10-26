# Bronze budgets (rolling context)

Local specialists have a hard `num_ctx`. When chat + tool schemas grow past a
**compress threshold**, middleware summarizes the middle (systems + summary +
last N turns) instead of sending an oversize request that returns empty.

Template middleware: [`middleware/alfred_middleware.py`](../../middleware/alfred_middleware.py).
Budgets file: [`deploy/compose/litellm/bronze_budgets.yaml`](../../deploy/compose/litellm/bronze_budgets.yaml).

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

Keep `bronze_budgets.yaml` mapping each alias → `{num_ctx, compress_threshold}`
and update it whenever you rewire context. Middleware prefers that file, then
falls back to reading `num_ctx` from LiteLLM `config.yaml`.

## Summarizer order (template honesty)

1. **Self-summarize** on the resident chat alias (`/api/chat`) — matches
   `OLLAMA_MAX_LOADED_MODELS=1` (no extra weight for Bronze).
2. **FIM fallback** via `/api/generate` on a small **base** tag (never `/api/chat`
   on base — it continues the transcript). Soft `keep_alive` (e.g. `2m`) only —
   **never** pin FIM with `keep_alive: -1`.
3. On failure while over threshold: **extractive stub** / hard-drop the middle so
   the specialist still fits.

Optional `CHROMA_URL` Bronze upsert is best-effort and must not block the chat.

## Homelab lesson

Thresholds that stay at “20k forever” while you wire a 16k model will look like
“the model is dumb” when the real bug is **overflow**. Budgets must follow the alias.
