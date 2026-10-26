#!/usr/bin/env bash
# Template SoT = this git tree. After editing skills/ or routing/domains.yaml,
# restart LiteLLM so mounts/callbacks re-read files (domains.yaml is cached by mtime).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$ROOT/deploy/compose"
cd "$COMPOSE_DIR"

if [[ ! -f .env ]]; then
  echo "FAIL: missing deploy/compose/.env — run scripts/bootstrap.sh first" >&2
  exit 1
fi

echo "==> restart alfred-litellm (skills + domains + middleware remount)"
docker compose restart litellm
echo "OK: litellm restarted @ $(date -Iseconds)"
echo "Tip: re-run scripts/smoke.sh after domain/skill edits."
