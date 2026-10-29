"""Audit findings upsert + baseline rollups for Sentinel telemetry DB."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from alfred_memory_rubric import utc_now_iso
from alfred_network_classify import network_finding_kinds

def upsert_finding(conn, run_id: int, category: str, fingerprint: str, title: str, detail: str, severity: str) -> bool:
    now = utc_now_iso()
    cur = conn.execute("SELECT id, occurrences FROM audit_findings WHERE fingerprint = ?", (fingerprint,))
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE audit_findings SET last_seen_at=?, last_run_id=?, occurrences=occurrences+1, "
            "title=?, detail=?, severity=? WHERE id=?",
            (now, run_id, title, detail, severity, row["id"]),
        )
        return False
    conn.execute(
        "INSERT INTO audit_findings (first_seen_at, last_seen_at, last_run_id, category, fingerprint, "
        "title, detail, severity, status, occurrences) VALUES (?,?,?,?,?,?,?,?, 'open', 1)",
        (now, now, run_id, category, fingerprint, title, detail, severity),
    )
    return True


def findings_from_metrics(conn, run_id: int, metrics: dict) -> list[str]:
    new_titles = []
    extra = json.loads(metrics.get("extra_json") or "{}")
    vram_used = metrics.get("vram_used_mb")
    vram_total = metrics.get("vram_total_mb")
    if vram_used and vram_total and vram_used / vram_total > 0.92:
        if upsert_finding(
            conn,
            run_id,
            "vram",
            "vram-high",
            "VRAM usage high",
            f"{vram_used}/{vram_total} MB",
            "advisory",
        ):
            new_titles.append("VRAM usage high")
    gpu = metrics.get("gpu_temp_c")
    if gpu and gpu >= 85:
        if upsert_finding(conn, run_id, "thermal", "gpu-hot", "GPU temperature high", f"{gpu}C", "critical"):
            new_titles.append("GPU temperature high")
    for name, status in (extra.get("services") or {}).items():
        if status != "ok" and name != "mcpo":
            fp = f"service-{name}-down"
            if upsert_finding(conn, run_id, "service", fp, f"{name} unhealthy", status, "critical"):
                new_titles.append(f"{name} unhealthy")
    docker = extra.get("docker") or {}
    for name in docker.get("unhealthy") or []:
        fp = f"docker-unhealthy-{name}"
        if upsert_finding(
            conn, run_id, "service", fp, f"Docker container unhealthy: {name}", "unhealthy", "critical"
        ):
            new_titles.append(f"Docker unhealthy: {name}")
    for name in docker.get("exited") or []:
        # Ignore one-shot helpers if any; flag persistent containers
        fp = f"docker-exited-{name}"
        if upsert_finding(
            conn, run_id, "service", fp, f"Docker container exited: {name}", "exited", "advisory"
        ):
            new_titles.append(f"Docker exited: {name}")
    for p in (extra.get("publish") or {}).get("docker_published") or []:
        if p.get("lan_reachable") and p.get("host_port") in {11434, 8000}:
            fp = f"publish-dangerous-{p.get('container')}-{p.get('host_port')}"
            if upsert_finding(
                conn,
                run_id,
                "network",
                fp,
                f"Dangerous LAN publish: {p.get('container')}:{p.get('host_port')}",
                json.dumps(p)[:240],
                "critical",
            ):
                new_titles.append(f"Dangerous LAN publish {p.get('container')}:{p.get('host_port')}")
    for mount, info in (extra.get("disks") or {}).items():
        free = info.get("free_gb")
        used_pct = info.get("used_pct")
        if isinstance(free, (int, float)) and free < 20:
            fp = f"disk-low-{mount.replace('/', '_')}"
            if upsert_finding(conn, run_id, "disk", fp, f"Low free space on {mount}", f"{free} GB", "advisory"):
                new_titles.append(f"Low free space on {mount}")
        elif isinstance(used_pct, (int, float)) and used_pct >= 80:
            fp = f"disk-fullish-{mount.replace('/', '_')}"
            sev = "critical" if used_pct >= 92 else "advisory"
            if upsert_finding(
                conn,
                run_id,
                "disk",
                fp,
                f"Disk nearly full on {mount}",
                f"{used_pct}% used, {free} GB free",
                sev,
            ):
                new_titles.append(f"Disk nearly full on {mount}")
    for mount, info in (extra.get("smart") or {}).items():
        overall = (info or {}).get("overall") or ""
        if overall and overall.upper() not in ("PASSED", "OK", "UNKNOWN") and "error" not in (info or {}):
            fp = f"smart-fail-{mount.replace('/', '_')}"
            if upsert_finding(conn, run_id, "disk", fp, f"SMART health issue on {mount}", overall, "critical"):
                new_titles.append(f"SMART health issue on {mount}")
        attrs = (info or {}).get("attrs") or {}
        for key in ("Reallocated_Sector_Ct", "Current_Pending_Sector", "Offline_Uncorrectable"):
            try:
                val = int(attrs.get(key) or 0)
            except ValueError:
                continue
            if val > 0:
                fp = f"smart-attr-{mount.replace('/', '_')}-{key}"
                if upsert_finding(
                    conn,
                    run_id,
                    "disk",
                    fp,
                    f"SMART {key} on {mount}",
                    str(val),
                    "advisory",
                ):
                    new_titles.append(f"SMART {key} on {mount}")
    unifi = extra.get("unifi") or {}
    loss = unifi.get("avg_loss_pct")
    for kind in network_finding_kinds(unifi):
        if kind == "unifi-loss-high":
            if upsert_finding(
                conn,
                run_id,
                "network",
                "unifi-loss-high",
                "LAN/WAN packet loss elevated",
                f"{loss}% avg loss · gateway {unifi.get('gateway')} · status {unifi.get('status')}",
                "critical" if isinstance(loss, (int, float)) and loss >= 20 else "advisory",
            ):
                new_titles.append("LAN/WAN packet loss elevated")
        elif kind == "unifi-unreachable":
            if upsert_finding(
                conn,
                run_id,
                "network",
                "unifi-unreachable",
                "LAN gateway/DNS unreachable",
                json.dumps(unifi.get("targets") or [])[:240],
                "critical",
            ):
                new_titles.append("LAN gateway/DNS unreachable")
        elif kind == "wan-unreachable":
            if upsert_finding(
                conn,
                run_id,
                "network",
                "wan-unreachable",
                "WAN probes all failed",
                json.dumps(
                    [t for t in (unifi.get("targets") or []) if t.get("role") == "wan-probe"]
                )[:240],
                "advisory",
            ):
                new_titles.append("WAN probes all failed")
    ctrl = unifi.get("controller") or {}
    alerts = ctrl.get("alerts") if isinstance(ctrl, dict) else None
    if ctrl.get("ok") and isinstance(alerts, list) and alerts:
        detail = "; ".join(str(a) for a in alerts[:8])[:240]
        if upsert_finding(
            conn,
            run_id,
            "network",
            "unifi-controller-alerts",
            "UniFi controller alerts",
            detail,
            "advisory",
        ):
            new_titles.append("UniFi controller alerts")
    elif isinstance(ctrl, dict) and ctrl.get("status") == "error":
        if upsert_finding(
            conn,
            run_id,
            "network",
            "unifi-controller-api-error",
            "UniFi controller API error",
            f"{ctrl.get('reason')}: {ctrl.get('detail')}"[:240],
            "advisory",
        ):
            new_titles.append("UniFi controller API error")
    conn.commit()
    return new_titles


def baseline_rollup(conn) -> str:
    lines = ["### Baselines (available fields)"]
    snapshots: list[tuple] = []
    for days in (30, 60, 90):
        since = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat()
        row = conn.execute(
            "SELECT AVG(gpu_temp_c) g, AVG(vram_used_mb) v, AVG(ram_used_mb) r, COUNT(*) n "
            "FROM telemetry_metrics WHERE captured_at >= ?",
            (since,),
        ).fetchone()
        snap = (
            row["n"],
            row["g"] and round(row["g"], 1),
            row["v"] and round(row["v"], 1),
            row["r"] and round(row["r"], 1),
        )
        snapshots.append((days, snap))
    if len({snap for _, snap in snapshots}) == 1:
        n, g, v, r = snapshots[0][1]
        window = "/".join(str(days) for days, _ in snapshots)
        lines.append(
            f"- {window}d identical (history shorter than the longest window): "
            f"n={n} avg_gpu={g} avg_vram_mb={v} avg_ram_mb={r}"
        )
        return "\n".join(lines)
    for days, (n, g, v, r) in snapshots:
        lines.append(
            f"- {days}d: n={n} avg_gpu={g} avg_vram_mb={v} avg_ram_mb={r}"
        )
    return "\n".join(lines)
