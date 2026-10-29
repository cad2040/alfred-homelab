"""Sentinel shared constants — all paths/env are generic and overridable."""
from __future__ import annotations

import os
from pathlib import Path

# Root for lab state (digests, telemetry, locks). Never hardcode private mounts.
DATA_ROOT = Path(os.environ.get("ALFRED_DATA_ROOT", "./alfred-data")).expanduser().resolve()

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
LITELLM = os.environ.get(
    "ALFRED_LITELLM_BASE",
    os.environ.get("LITELLM_BASE", "http://127.0.0.1:4000/v1"),
).rstrip("/")
if not LITELLM.endswith("/v1"):
    # accept http://127.0.0.1:4000 or .../v1
    LITELLM = LITELLM.rstrip("/") + "/v1"

_chroma_host = os.environ.get("ALFRED_CHROMA_HOST", "127.0.0.1")
_chroma_port = os.environ.get("ALFRED_CHROMA_PORT", "8000")
CHROMA = os.environ.get(
    "ALFRED_CHROMA_HTTP",
    f"http://{_chroma_host}:{_chroma_port}/api/v2/tenants/default_tenant/databases/default_database",
)

LOCK_PATH = Path(
    os.environ.get("SENTINEL_LOCK", str(DATA_ROOT / "locks" / "vram.lock"))
).expanduser()
DIGEST_DIR = Path(
    os.environ.get("DIGEST_DIR", str(DATA_ROOT / "digests" / "morning"))
).expanduser()
LITELLM_CONFIG = Path(
    os.environ.get(
        "LITELLM_CONFIG",
        os.environ.get("ALFRED_LITELLM_CONFIG", "./deploy/compose/litellm/config.yaml"),
    )
).expanduser()
STAGED_MODEL_UPGRADES = Path(
    os.environ.get("STAGED_MODEL_UPGRADES", str(DATA_ROOT / "staged_promotions" / "model_upgrades"))
).expanduser()

# Comma-separated absolute mounts to chart (empty = skip disk section).
# Example: SENTINEL_DISK_MOUNTS=/,/var,/data
DISK_MOUNTS = tuple(
    m.strip()
    for m in os.environ.get("SENTINEL_DISK_MOUNTS", "/").split(",")
    if m.strip()
)

REASONER_TAG = os.environ.get("SENTINEL_REASONER_MODEL", "alfred-reasoner")
CODER_TAG = os.environ.get("SENTINEL_CODER_MODEL", "alfred-coder-14b")
SECURITY_TAG = os.environ.get("SENTINEL_SECURITY_MODEL", "alfred-security")
EMBED_TAG = os.environ.get("ALFRED_EMBED_MODEL", "nomic-embed-text")
BRONZE = os.environ.get("ALFRED_BRONZE_COLLECTION", "ephemeral_working_context")
GOLD = os.environ.get("ALFRED_GOLD_COLLECTION", "curated_skills_registry")

LITELLM_RETRIES = int(os.environ.get("ALFRED_SENTINEL_LLM_RETRIES", "3"))
LITELLM_BACKOFF_S = float(os.environ.get("ALFRED_SENTINEL_LLM_BACKOFF_S", "8"))
RETRYABLE_MARKERS = (
    "HTTP 500",
    "HTTP 502",
    "HTTP 503",
    "HTTP 504",
    "timed out",
    "Timeout",
    "timeout",
    "Connection reset",
    "ConnectionResetError",
    "RemoteDisconnected",
    "IncompleteRead",
    "Temporary failure",
    "Broken pipe",
)

# Optional post-digest shell commands (space-separated tokens not supported —
# use a wrapper script path). Empty = skip.
BACKUP_CMD = (os.environ.get("SENTINEL_BACKUP_CMD") or "").strip()
ENABLE_MEMORY_STAGE4 = os.environ.get("SENTINEL_ENABLE_MEMORY", "0").strip() not in {
    "0", "false", "no", ""
}
ENABLE_CONTROLLER_API = os.environ.get("SENTINEL_ENABLE_CONTROLLER_API", "0").strip() not in {
    "0", "false", "no", ""
}
