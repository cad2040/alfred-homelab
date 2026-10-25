# Automated eval harness

The harness is how Alfred stays honest: **fixed prompts → call an alias → gate the answer** (and optionally ask a cloud Flash model to comment). Green matrix ≠ unsupervised agent. HITL required to change prod.

## Why bother

Local 7B/9B models regress silently when you:

- tweak a Gold skill
- rewire an alias
- change `num_ctx` / Bronze thresholds
- “helpfully” loosen a never-rule

A short, boring matrix catches that before Monday’s chat feels “off.”

## Shape of a harness

```text
challenges/*.md          # user prompts (and expected behaviours in comments/docs)
run_challenge.py         # POST /v1/chat/completions → response.md + meta.json
eval_*.py / inline gates # PASS/FAIL JSON
run_*_batch.sh           # orchestrate a pack
optional judge           # Gemini Flash advisory over the matrix summary
```

## Packs (typical private lab)

| Pack | Intent |
|------|--------|
| Units / dense coding | concurrency, pools, SQL races |
| Spec Kit | `#domain:` discipline, refuse fake domains |
| Sysadmin | disk-usage path fidelity, safe-script KEEP/DROP |
| Sentinel contracts | security/stability prompt shapes |
| Model challenge | candidate vs baseline alias (see model-challenge guide) |

You do **not** need all packs on day one. Start with **one gate that encodes a scar**.

## Minimal example in this repo

See [`examples/harness/`](../../examples/harness/):

```bash
export LITELLM_BASE=http://127.0.0.1:4000
export LITELLM_MASTER_KEY=...   # from your .env — do not commit
cd examples/harness
python3 run_challenge.py \
  --prompt-file challenges/01_docker_ufw_hint.md \
  --out-dir runs/01_demo \
  --model alfred-coder
python3 eval_keywords.py --response runs/01_demo/response.md --need docker-user,ufw
```

## Weekly loop (pattern)

1. **Sunday / off-peak:** run matrix (skip dense if VRAM-tight).
2. **Judge (optional):** Flash model scores batches; suggestions are drafts only.
3. **Monday:** human reads HTML/markdown report; apply skill fixes by hand.
4. **Never** auto-promote Gold or auto-wire models from a judge score.

Env for a judge (private `.env` only):

```bash
GEMINI_API_KEY=...          # or GOOGLE_API_KEY
GEMINI_MODEL=gemini-2.0-flash  # pick a current Flash; advisory only
```

## Writing a good challenge

1. Reproduce a **real** failure (invented `/mnt/media`, missing `DOCKER-USER`, etc.).
2. Gate on **observable** strings/structure — not vibes.
3. Keep prompts short enough for your `num_ctx`.
4. Disable tools for coding evals if tools divert into note-taking.
5. Archive old challenge text when you change expectations.

## Trust bands (example language)

| Band | Meaning |
|------|---------|
| Red | Do not trust for that domain without HITL every turn |
| Amber | OK with `#domain:` + review |
| Green | Pack stable; still no unsupervised prod mutations |

Matrix green moves a band — it does not grant shell freedom.
