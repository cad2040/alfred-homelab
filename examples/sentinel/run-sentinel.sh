#!/usr/bin/env bash
# Load optional env file, then run the orchestrator.
# Usage:
#   ALFRED_ENV_FILE=/path/to/private.env ./run-sentinel.sh
#   ./run-sentinel.sh          # uses already-exported env
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ALFRED_ENV_FILE:-}"
if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
export PYTHONPATH="${HERE}/lib${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "${HERE}/alfred-sentinel.py" "$@"
