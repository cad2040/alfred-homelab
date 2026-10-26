# Minimal eval harness examples (keyword toy)

Optional depth after smoke — not part of day-1 bootstrap. Not a full weekly
matrix; just enough to prove “fixed prompt → gate response.”

```bash
export LITELLM_BASE=http://127.0.0.1:4000
export LITELLM_MASTER_KEY=...   # from deploy/compose/.env — never commit

python3 run_challenge.py \
  --prompt-file challenges/01_docker_ufw_hint.md \
  --out-dir runs/01 \
  --model alfred-coder

python3 eval_keywords.py \
  --response runs/01/response.md \
  --need docker-user,127.0.0.1 \
  --forbid 'ufw allow'

python3 run_challenge.py \
  --prompt-file challenges/02_safe_script_dry_run.md \
  --out-dir runs/02 \
  --model alfred-coder

python3 eval_keywords.py \
  --response runs/02/response.md \
  --need 'set -euo,CONFIRM,KEEP=,DROP=' \
  --forbid 'ln -s'
```

Grow privately: route dumps, Spec Kit domain gates, weekly Flash judge.
See [docs/guides/eval-harness.md](../../docs/guides/eval-harness.md).
