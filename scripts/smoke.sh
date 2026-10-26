#!/usr/bin/env bash
# Smoke LiteLLM + skill inject (DOCKER-USER) + Coach phrase trigger.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$ROOT/deploy/compose"
cd "$COMPOSE_DIR"

# shellcheck disable=SC1091
set -a
source .env
set +a

KEY="${LITELLM_MASTER_KEY:?set LITELLM_MASTER_KEY in deploy/compose/.env}"
BASE="${ALFRED_LITELLM_URL:-http://127.0.0.1:4000}"

echo "==> /v1/models"
curl -sfS "$BASE/v1/models" -H "Authorization: Bearer $KEY" | head -c 400
echo
echo

echo "==> chat #domain:docker-ufw (expect DOCKER-USER in reply)"
REPLY=$(curl -sfS "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"alfred-coder","messages":[{"role":"user","content":"#domain:docker-ufw\nWhy is UFW not enough for Docker publishes? Answer in 5 bullets."}],"max_tokens":350}')
echo "$REPLY" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["choices"][0]["message"]["content"])' | tee /tmp/alfred-smoke-docker.txt
if ! grep -qi 'DOCKER-USER\|docker-user' /tmp/alfred-smoke-docker.txt; then
  echo "FAIL: expected DOCKER-USER in skill-aware reply" >&2
  exit 1
fi
echo "PASS: docker-ufw inject"
echo

echo "==> Coach this Prompt: (expect Coached prompt / Issue sections)"
REPLY=$(curl -sfS "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"alfred-reasoner","messages":[{"role":"user","content":"Coach this Prompt:\nI want to lock my Ollama ports to localhost only."}],"max_tokens":500}')
echo "$REPLY" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["choices"][0]["message"]["content"])' | tee /tmp/alfred-smoke-coach.txt
if ! grep -qiE 'Coached prompt|## Issue' /tmp/alfred-smoke-coach.txt; then
  echo "FAIL: expected Coach this Prompt structure" >&2
  exit 1
fi
echo "PASS: coach phrase inject"
echo
echo "OK: smoke passed"
