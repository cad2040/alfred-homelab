#!/usr/bin/env bash
# Bring up the Alfred deploy template (Ollama + LiteLLM) and pull default tags.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$ROOT/deploy/compose"
cd "$COMPOSE_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created deploy/compose/.env — set LITELLM_MASTER_KEY to a long random string."
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

if [[ -z "${LITELLM_MASTER_KEY:-}" || "$LITELLM_MASTER_KEY" == "change-me-to-a-long-random-string" ]]; then
  echo "WARN: LITELLM_MASTER_KEY still default — edit deploy/compose/.env before exposing anything." >&2
fi

CPU_FLAG=()
if [[ "${ALFRED_CPU:-0}" == "1" ]]; then
  CPU_FLAG=(-f docker-compose.yml -f docker-compose.cpu.yml)
fi

echo "==> docker compose up -d"
docker compose "${CPU_FLAG[@]}" up -d

CODER_TAG="${ALFRED_CODER_TAG:-qwen2.5-coder:7b-instruct}"
REASONER_TAG="${ALFRED_REASONER_TAG:-qwen2.5:7b-instruct}"
echo "==> ollama pull $CODER_TAG"
docker exec alfred-ollama ollama pull "$CODER_TAG"
if [[ "$REASONER_TAG" != "$CODER_TAG" ]]; then
  echo "==> ollama pull $REASONER_TAG"
  docker exec alfred-ollama ollama pull "$REASONER_TAG"
fi

if [[ "${ALFRED_PULL_FIM:-0}" == "1" ]]; then
  FIM_TAG="${ALFRED_FIM_TAG:-qwen2.5-coder:1.5b-base}"
  echo "==> ollama pull $FIM_TAG (Bronze fallback)"
  docker exec alfred-ollama ollama pull "$FIM_TAG"
fi

echo
echo "OK: stack is up. Next:"
echo "  $ROOT/scripts/smoke.sh"
echo "Clients: http://127.0.0.1:4000/v1  (Bearer \$LITELLM_MASTER_KEY)"
