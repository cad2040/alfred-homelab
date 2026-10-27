#!/usr/bin/env bash
# Smoke LiteLLM + skill inject (DOCKER-USER) + Coach phrase trigger.
# Requires: curl. Optional: python3 or jq (pretty-print only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$ROOT/deploy/compose"
cd "$COMPOSE_DIR"

if [[ ! -f .env ]]; then
  echo "FAIL: missing deploy/compose/.env — run scripts/bootstrap.sh first" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

if ! command -v curl >/dev/null 2>&1; then
  echo "FAIL: curl is required for smoke.sh" >&2
  exit 1
fi

KEY="${LITELLM_MASTER_KEY:?set LITELLM_MASTER_KEY in deploy/compose/.env}"
if [[ "$KEY" == "change-me-to-a-long-random-string" ]]; then
  echo "FAIL: set a real LITELLM_MASTER_KEY in deploy/compose/.env before smoke" >&2
  exit 1
fi
BASE="${ALFRED_LITELLM_URL:-http://127.0.0.1:4000}"

echo "==> wait for LiteLLM at $BASE"
ready=0
for _ in $(seq 1 60); do
  if curl -sfS "$BASE/v1/models" -H "Authorization: Bearer $KEY" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != "1" ]]; then
  echo "FAIL: LiteLLM not answering /v1/models after ~2m" >&2
  exit 1
fi

print_content() {
  # Pretty-print message content when python3 or jq exists; else raw JSON.
  local raw="$1"
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$raw" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["choices"][0]["message"].get("content") or "")' 2>/dev/null && return
  fi
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$raw" | jq -r '.choices[0].message.content // empty' 2>/dev/null && return
  fi
  printf '%s\n' "$raw"
}

echo "==> /v1/models"
curl -sfS "$BASE/v1/models" -H "Authorization: Bearer $KEY" | head -c 400
echo
echo

TMPDIR_SMOKE="${TMPDIR:-/tmp}"
DOCKER_OUT="$TMPDIR_SMOKE/alfred-smoke-docker.json"
COACH_OUT="$TMPDIR_SMOKE/alfred-smoke-coach.json"

echo "==> chat #domain:docker-ufw (expect DOCKER-USER in reply)"
REPLY=$(curl -sfS "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"alfred-coder","messages":[{"role":"user","content":"#domain:docker-ufw\nWhy is UFW not enough for Docker publishes? Answer in 5 bullets."}],"max_tokens":350}')
printf '%s' "$REPLY" >"$DOCKER_OUT"
print_content "$REPLY"
# Gate on raw JSON so python3/jq are optional (content still contains the tokens).
if ! grep -qiE 'DOCKER-USER|docker-user' "$DOCKER_OUT"; then
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
printf '%s' "$REPLY" >"$COACH_OUT"
print_content "$REPLY"
if ! grep -qiE 'Coached prompt|## Issue' "$COACH_OUT"; then
  echo "FAIL: expected Coach this Prompt structure" >&2
  exit 1
fi
echo "PASS: coach phrase inject"
echo
echo "OK: smoke passed"
echo "  (optional pretty-print used python3 or jq if installed)"
