"""Alfred Sentinel local telemetry store (SQLite WAL).

DB path via ALFRED_TELEMETRY_DB or ALFRED_DATA_ROOT/telemetry/telemetry.db.


Retention (prune_retention, called by Sentinel nightly):
  - telemetry_metrics: rolling 90 days (30/60/90 baselines)
  - audit_findings with status=resolved: 180 days after resolved_at
  - runs: 180 days (CASCADE drops orphan metrics / compaction rows)
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get(
    "ALFRED_TELEMETRY_DB",
    str(Path(os.environ.get("ALFRED_DATA_ROOT", "./alfred-data")) / "telemetry" / "telemetry.db"),
))

METRICS_RETENTION_DAYS = int(os.environ.get("ALFRED_TELEMETRY_METRICS_DAYS", "90"))
RESOLVED_FINDINGS_RETENTION_DAYS = int(
    os.environ.get("ALFRED_TELEMETRY_RESOLVED_FINDINGS_DAYS", "180")
)
RUNS_RETENTION_DAYS = int(os.environ.get("ALFRED_TELEMETRY_RUNS_DAYS", "180"))

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    duration_sec    REAL,
    status          TEXT NOT NULL,
    models_invoked  TEXT,
    trigger         TEXT NOT NULL DEFAULT 'cron',
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);

CREATE TABLE IF NOT EXISTS telemetry_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    captured_at     TEXT NOT NULL,
    gpu_temp_c      REAL,
    cpu_temp_c      REAL,
    vram_used_mb    REAL,
    vram_total_mb   REAL,
    ram_used_mb     REAL,
    ram_total_mb    REAL,
    disk_smart_json TEXT,
    unifi_ping_ms   REAL,
    unifi_loss_pct  REAL,
    extra_json      TEXT
);
CREATE INDEX IF NOT EXISTS idx_metrics_run ON telemetry_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_metrics_captured ON telemetry_metrics(captured_at);

CREATE TABLE IF NOT EXISTS audit_findings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    last_run_id     INTEGER REFERENCES runs(id),
    category        TEXT NOT NULL,
    fingerprint     TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    detail          TEXT,
    severity        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open',
    occurrences     INTEGER NOT NULL DEFAULT 1,
    resolved_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_findings_status ON audit_findings(status);
CREATE INDEX IF NOT EXISTS idx_findings_category ON audit_findings(category);
CREATE INDEX IF NOT EXISTS idx_findings_resolved ON audit_findings(resolved_at);

CREATE TABLE IF NOT EXISTS memory_compaction_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    compacted_at        TEXT NOT NULL,
    chunks_evaluated    INTEGER NOT NULL DEFAULT 0,
    chunks_pruned       INTEGER NOT NULL DEFAULT 0,
    silver_pinned       INTEGER NOT NULL DEFAULT 0,
    gold_ratified       INTEGER NOT NULL DEFAULT 0,
    gold_staged         INTEGER NOT NULL DEFAULT 0,
    pending_review_swept INTEGER NOT NULL DEFAULT 0,
    details_json        TEXT
);
CREATE INDEX IF NOT EXISTS idx_compaction_run ON memory_compaction_log(run_id);
"""

# Columns added after the first ship — CREATE IF NOT EXISTS will not alter
# existing tables, so init_schema migrates these.
_COMPACTION_EXTRA_COLS: tuple[tuple[str, str], ...] = (
    ("gold_ratified", "INTEGER NOT NULL DEFAULT 0"),
    ("gold_staged", "INTEGER NOT NULL DEFAULT 0"),
    ("pending_review_swept", "INTEGER NOT NULL DEFAULT 0"),
)


def _utc_cutoff_iso(days: int) -> str:
    return (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).replace(microsecond=0).isoformat()


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] if isinstance(r, sqlite3.Row) else r[1] for r in rows}


def migrate_schema(conn: sqlite3.Connection) -> list[str]:
    """Additive ALTERs for DBs created before gold_ratified / pending columns."""
    applied: list[str] = []
    if not _table_columns(conn, "memory_compaction_log"):
        return applied
    existing = _table_columns(conn, "memory_compaction_log")
    for col, decl in _COMPACTION_EXTRA_COLS:
        if col not in existing:
            conn.execute(
                f"ALTER TABLE memory_compaction_log ADD COLUMN {col} {decl}"
            )
            applied.append(f"memory_compaction_log.{col}")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_findings_resolved ON audit_findings(resolved_at)"
    )
    return applied


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    migrate_schema(conn)
    conn.commit()


def consistent_backup_copy(conn: sqlite3.Connection, dest: Path) -> None:
    """Online-consistent SQLite snapshot for backup tools (optional)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(dest) as dest_conn:
        conn.backup(dest_conn)


def prune_retention(
    conn: sqlite3.Connection,
    *,
    metrics_days: int | None = None,
    resolved_findings_days: int | None = None,
    runs_days: int | None = None,
) -> dict[str, int]:
    """Delete aged rows per locked retention. Safe to call every Sentinel run.

    Order: metrics → resolved findings → runs (CASCADE cleans children).
    Open findings are never pruned by age.
    """
    m_days = METRICS_RETENTION_DAYS if metrics_days is None else metrics_days
    f_days = (
        RESOLVED_FINDINGS_RETENTION_DAYS
        if resolved_findings_days is None
        else resolved_findings_days
    )
    r_days = RUNS_RETENTION_DAYS if runs_days is None else runs_days

    metrics_cut = _utc_cutoff_iso(m_days)
    findings_cut = _utc_cutoff_iso(f_days)
    runs_cut = _utc_cutoff_iso(r_days)

    cur = conn.execute(
        "DELETE FROM telemetry_metrics WHERE captured_at < ?",
        (metrics_cut,),
    )
    metrics_deleted = cur.rowcount if cur.rowcount is not None else 0

    cur = conn.execute(
        "DELETE FROM audit_findings "
        "WHERE status = 'resolved' "
        "AND resolved_at IS NOT NULL "
        "AND resolved_at < ?",
        (findings_cut,),
    )
    findings_deleted = cur.rowcount if cur.rowcount is not None else 0

    # findings.last_run_id has no ON DELETE action — null it before run delete
    conn.execute(
        "UPDATE audit_findings SET last_run_id = NULL "
        "WHERE last_run_id IN (SELECT id FROM runs WHERE started_at < ?)",
        (runs_cut,),
    )
    cur = conn.execute(
        "DELETE FROM runs WHERE started_at < ?",
        (runs_cut,),
    )
    runs_deleted = cur.rowcount if cur.rowcount is not None else 0

    conn.commit()
    return {
        "metrics_deleted": int(metrics_deleted),
        "resolved_findings_deleted": int(findings_deleted),
        "runs_deleted": int(runs_deleted),
        "metrics_days": m_days,
        "resolved_findings_days": f_days,
        "runs_days": r_days,
    }


if __name__ == "__main__":
    c = connect()
    init_schema(c)
    mode = c.execute("PRAGMA journal_mode;").fetchone()[0]
    stats = prune_retention(c)
    print(f"telemetry.db ready journal_mode={mode} path={DB_PATH} prune={stats}")
