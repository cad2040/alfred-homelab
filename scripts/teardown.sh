#!/usr/bin/env bash
# Stop the template stack. Pass --volumes to also remove the Ollama weight volume.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$ROOT/deploy/compose"
cd "$COMPOSE_DIR"

ARGS=(down)
if [[ "${1:-}" == "--volumes" || "${1:-}" == "-v" ]]; then
  ARGS+=( -v )
  echo "WARN: removing ollama_data volume (weights will be deleted)" >&2
fi

docker compose "${ARGS[@]}"
echo "OK: stack stopped"
