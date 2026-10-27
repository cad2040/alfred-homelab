#!/usr/bin/env bash
# Bring up the Alfred deploy template and wire reference Ollama tags.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$ROOT/deploy/compose"
MODELFILES="$ROOT/deploy/modelfiles"
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
  echo "WARN: ALFRED_CPU=1 — stack will start, but 14B/9B inference is very slow." >&2
  echo "      Prefer a GPU host for day-to-day use; CPU is for bring-up checks only." >&2
fi

echo "==> docker compose up -d"
docker compose "${CPU_FLAG[@]}" up -d

echo "==> wait for ollama"
ready=0
for _ in $(seq 1 60); do
  if docker exec alfred-ollama ollama list >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != "1" ]]; then
  echo "FAIL: alfred-ollama not ready after ~2m" >&2
  exit 1
fi

CODER_BASE="${ALFRED_CODER_BASE:-qwen2.5-coder:14b-instruct-q3_K_M}"
REASONER_BASE="${ALFRED_REASONER_BASE:-qwen3.5:9b}"
SECURITY_BASE="${ALFRED_SECURITY_BASE:-hf.co/mradermacher/Foundation-Sec-8B-Instruct-GGUF:Q4_K_M}"

echo "==> ollama pull base weights (large; plan disk + time)"
docker exec alfred-ollama ollama pull "$CODER_BASE"
docker exec alfred-ollama ollama pull "$REASONER_BASE"
docker exec alfred-ollama ollama pull "$SECURITY_BASE"

if [[ "${ALFRED_PULL_FIM:-0}" == "1" ]]; then
  FIM_TAG="${ALFRED_FIM_TAG:-qwen2.5-coder:1.5b-base}"
  echo "==> ollama pull $FIM_TAG (Bronze fallback)"
  docker exec alfred-ollama ollama pull "$FIM_TAG"
fi

create_from_modelfile() {
  local tag="$1"
  local file="$2"
  local remote="/tmp/${tag}.Modelfile"
  if [[ ! -f "$file" ]]; then
    echo "FAIL: missing Modelfile $file" >&2
    exit 1
  fi
  echo "==> ollama create $tag from $(basename "$file")"
  # ollama create does not accept Modelfile on stdin (-f -); copy then create.
  docker cp "$file" "alfred-ollama:${remote}"
  docker exec alfred-ollama ollama create "$tag" -f "$remote"
}

create_from_modelfile alfred-coder-14b "$MODELFILES/alfred-coder-14b.Modelfile"
create_from_modelfile alfred-reasoner "$MODELFILES/alfred-reasoner.Modelfile"
create_from_modelfile alfred-planner "$MODELFILES/alfred-planner.Modelfile"
create_from_modelfile alfred-foundation-sec "$MODELFILES/alfred-foundation-sec.Modelfile"

echo "==> wait for LiteLLM"
# shellcheck disable=SC1091
set -a
source .env
set +a
LL_KEY="${LITELLM_MASTER_KEY:-}"
ll_ready=0
for _ in $(seq 1 60); do
  if [[ -n "$LL_KEY" && "$LL_KEY" != "change-me-to-a-long-random-string" ]] \
    && curl -sfS "http://127.0.0.1:4000/v1/models" -H "Authorization: Bearer $LL_KEY" >/dev/null 2>&1; then
    ll_ready=1
    break
  fi
  # Key still default: only check TCP/HTTP reaches the proxy
  if curl -sfS "http://127.0.0.1:4000/health/liveliness" >/dev/null 2>&1 \
    || curl -sfS "http://127.0.0.1:4000/health" >/dev/null 2>&1 \
    || curl -sS -o /dev/null -w '' "http://127.0.0.1:4000/v1/models" >/dev/null 2>&1; then
    ll_ready=1
    break
  fi
  sleep 2
done
if [[ "$ll_ready" != "1" ]]; then
  echo "WARN: LiteLLM not answering yet — check: docker logs alfred-litellm" >&2
fi

echo
echo "OK: stack is up; aliases match docs/architecture.md."
echo "  Disk note: 14B Q3 + 9B + Foundation-Sec is tens of GB — expected."
echo "  VRAM: OLLAMA_MAX_LOADED_MODELS=1 (one specialist at a time)."
echo "  Scope: no digests/search/DR — see docs/PRIVATE_VS_TEMPLATE.md."
echo "Next:"
echo "  edit deploy/compose/.env  # set LITELLM_MASTER_KEY (required for smoke)"
echo "  $ROOT/scripts/smoke.sh    # needs curl; python3/jq optional"
echo "Clients: http://127.0.0.1:4000/v1  (Bearer \$LITELLM_MASTER_KEY)"
