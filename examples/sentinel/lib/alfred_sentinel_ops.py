"""Post-digest ops: backups, digest prune, optional eval hooks."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from alfred_sentinel_config import DATA_ROOT, DIGEST_DIR
from alfred_sentinel_runtime import log


def _eval_weekly_bin() -> list[str] | None:
    """Resolve optional eval-weekly CLI if the operator installed one."""
    for cand in (
        Path(os.environ.get("SENTINEL_EVAL_WEEKLY_BIN", "")),
        Path("/usr/local/bin/alfred-eval-weekly"),
    ):
        if cand.is_file() and os.access(cand, os.X_OK):
            return [str(cand)]
    return None


def maybe_monday_performance_mail() -> str:
    """Optional Monday hook — disabled unless SENTINEL_ENABLE_EVAL_HOOKS=1."""
    if os.environ.get("SENTINEL_ENABLE_EVAL_HOOKS", "0").strip() in {"0", "false", "no", ""}:
        return "skip-disabled"
    if datetime.now().weekday() != 0:
        return "skip-not-monday"
    pending = Path(
        os.environ.get(
            "SENTINEL_EVAL_PENDING_MAIL",
            str(DATA_ROOT / "digests" / "eval-matrix" / "pending_monday.md"),
        )
    )
    if not pending.is_file():
        return "skip-no-pending"
    cmd = _eval_weekly_bin()
    if not cmd:
        return "skip-no-eval-weekly-bin"
    try:
        r = subprocess.run([*cmd, "--monday-hook"], text=True, capture_output=True, check=False, timeout=120)
        tail = ((r.stdout or "") + (r.stderr or ""))[-300:]
        return f"monday-mail:{'ok' if r.returncode == 0 else 'fail'}:{tail}"
    except Exception as exc:  # noqa: BLE001
        return f"monday-mail-exc:{exc}"


def spawn_sunday_eval_matrix() -> str:
    """Optional Sunday hook — disabled unless SENTINEL_ENABLE_EVAL_HOOKS=1."""
    if os.environ.get("SENTINEL_ENABLE_EVAL_HOOKS", "0").strip() in {"0", "false", "no", ""}:
        return "skip-disabled"
    if datetime.now().weekday() != 6:
        return "skip-not-sunday"
    cmd = _eval_weekly_bin()
    if not cmd:
        return "skip-no-eval-weekly-bin"
    log_dir = Path(os.environ.get("SENTINEL_EVAL_LOG_DIR", str(DATA_ROOT / "digests" / "eval-matrix")))
    log_dir.mkdir(parents=True, exist_ok=True)
    out = log_dir / f"sunday_hook_{datetime.now().strftime('%Y%m%d')}.spawn.log"
    try:
        with out.open("ab") as fh:
            fh.write(f"\n# spawn {datetime.now(timezone.utc).isoformat()} cmd={cmd}\n".encode())
            fh.flush()
            subprocess.Popen(  # noqa: S603
                [*cmd, "--sunday-hook"],
                stdout=fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ},
            )
        return f"spawned:{out}"
    except Exception as exc:  # noqa: BLE001
        return f"spawn-fail:{exc}"


def run_backups() -> str:
    """Optional: set SENTINEL_BACKUP_CMD to a wrapper script path."""
    from alfred_sentinel_config import BACKUP_CMD

    if not BACKUP_CMD:
        return "backups:skip"
    try:
        r = subprocess.run(
            BACKUP_CMD,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
            timeout=1800,
        )
        return (
            f"backup_cmd:{'ok' if r.returncode == 0 else 'fail'} "
            f"{(r.stderr or r.stdout or '')[-300:]}"
        )
    except Exception as exc:  # noqa: BLE001
        return f"backup_cmd:exc:{exc}"


def prune_digests(days: int | None = None) -> int:
    days = int(os.environ.get("SENTINEL_DIGEST_RETENTION_DAYS", "7")) if days is None else days
    root = DIGEST_DIR.parent if DIGEST_DIR.name == "morning" else DIGEST_DIR
    root = Path(os.environ.get("DIGEST_ROOT", str(root)))
    if not root.is_dir():
        return 0
    cutoff = time.time() - days * 86400
    n = 0
    for p in root.rglob("*"):
        if p.is_file() and p.stat().st_mtime < cutoff:
            p.unlink(missing_ok=True)
            n += 1
    return n
