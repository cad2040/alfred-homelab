"""Host / Docker / network telemetry collectors for Sentinel."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

from alfred_memory_rubric import utc_now_iso
from alfred_network_classify import classify_network_from_targets
from alfred_controller_api import collect_controller_telemetry
from alfred_sentinel_config import DISK_MOUNTS, OLLAMA

def collect_host_metrics() -> dict:
    metrics: dict = {
        "captured_at": utc_now_iso(),
        "gpu_temp_c": None,
        "cpu_temp_c": None,
        "vram_used_mb": None,
        "vram_total_mb": None,
        "ram_used_mb": None,
        "ram_total_mb": None,
        "disk_smart_json": None,
        "unifi_ping_ms": None,
        "unifi_loss_pct": None,
        "extra_json": None,
    }
    extra: dict = {}
    # RAM
    try:
        mem = Path("/proc/meminfo").read_text(encoding="utf-8")
        vals = {}
        for line in mem.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                vals[k] = int(v.strip().split()[0])
        total = vals.get("MemTotal", 0) / 1024.0
        avail = vals.get("MemAvailable", 0) / 1024.0
        metrics["ram_total_mb"] = round(total, 1)
        metrics["ram_used_mb"] = round(total - avail, 1)
    except Exception as exc:  # noqa: BLE001
        extra["ram_error"] = str(exc)

    # NVIDIA
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=15,
        ).strip()
        temp, used, total = [x.strip() for x in out.split(",")]
        metrics["gpu_temp_c"] = float(temp)
        metrics["vram_used_mb"] = float(used)
        metrics["vram_total_mb"] = float(total)
    except Exception as exc:  # noqa: BLE001
        extra["gpu_error"] = str(exc)

    # CPU temp (thermal zone)
    try:
        for p in sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp")):
            val = int(p.read_text().strip()) / 1000.0
            if val > 0:
                metrics["cpu_temp_c"] = val
                break
    except Exception as exc:  # noqa: BLE001
        extra["cpu_temp_error"] = str(exc)

    # Disk free + used% for mounts listed in SENTINEL_DISK_MOUNTS
    disks = {}
    for mount in DISK_MOUNTS:
        try:
            u = shutil.disk_usage(mount)
            total_gb = round(u.total / 1e9, 1)
            free_gb = round(u.free / 1e9, 1)
            used_pct = round(100.0 * (1.0 - (u.free / u.total)), 1) if u.total else None
            source = ""
            try:
                source = subprocess.check_output(
                    ["findmnt", "-n", "-o", "SOURCE", mount],
                    text=True,
                    timeout=5,
                ).strip()
            except Exception:  # noqa: BLE001
                pass
            disks[mount] = {
                "total_gb": total_gb,
                "free_gb": free_gb,
                "used_pct": used_pct,
                "source": source or None,
            }
        except Exception as exc:  # noqa: BLE001
            disks[mount] = {"error": str(exc)}
    extra["disks"] = disks

    # Lightweight SMART health (best-effort; requires smartctl + permissions)
    smart: dict = {}
    for mount, info in disks.items():
        src = (info or {}).get("source") or ""
        # Strip partition suffix for SMART (e.g. /dev/nvme0n1p1 → /dev/nvme0n1)
        dev = re.sub(r"p?\d+$", "", src) if src.startswith("/dev/") else src
        if not dev.startswith("/dev/"):
            continue
        try:
            out = subprocess.check_output(
                ["sudo", "-n", "smartctl", "-H", "-A", "-n", "standby", dev],
                text=True,
                timeout=20,
                stderr=subprocess.STDOUT,
            )
            overall = "UNKNOWN"
            for line in out.splitlines():
                if "SMART overall-health" in line or "SMART Health Status" in line:
                    overall = line.split(":")[-1].strip()
                    break
            # Keep a short attribute digest for common fail indicators
            attrs = {}
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 10 and parts[0].isdigit():
                    name = parts[1]
                    if name in (
                        "Reallocated_Sector_Ct",
                        "Current_Pending_Sector",
                        "Offline_Uncorrectable",
                        "Temperature_Celsius",
                        "Power_On_Hours",
                    ):
                        attrs[name] = parts[9] if len(parts) > 9 else parts[-1]
            smart[mount] = {"device": dev, "overall": overall, "attrs": attrs}
        except Exception as exc:  # noqa: BLE001
            smart[mount] = {"device": src or None, "error": str(exc)[:160]}
    extra["smart"] = smart
    try:
        metrics["disk_smart_json"] = json.dumps(smart)
    except Exception:  # noqa: BLE001
        metrics["disk_smart_json"] = None

    # Endpoint soft checks — override with SENTINEL_SERVICE_URLS=name=url,name=url
    services = {}
    default_svcs = (
        ("ollama", f"{OLLAMA}/api/tags"),
        ("chroma", "http://127.0.0.1:8000/api/v2/heartbeat"),
        ("litellm", "http://127.0.0.1:4000/health/liveliness"),
        ("open-webui", "http://127.0.0.1:3000/"),
    )
    raw_svcs = (os.environ.get("SENTINEL_SERVICE_URLS") or "").strip()
    if raw_svcs:
        pairs = []
        for part in raw_svcs.split(","):
            if "=" not in part:
                continue
            n, u = part.split("=", 1)
            n, u = n.strip(), u.strip()
            if n and u:
                pairs.append((n, u))
        svc_list = pairs or list(default_svcs)
    else:
        svc_list = list(default_svcs)
    for name, url in svc_list:
        try:
            urllib.request.urlopen(url, timeout=3).read(64)
            services[name] = "ok"
        except Exception as exc:  # noqa: BLE001
            services[name] = f"fail:{exc.__class__.__name__}"
    extra["services"] = services

    # All Docker containers on this host
    extra["docker"] = collect_docker_containers()

    # Host publish posture + DOCKER-USER facts (security SoT)
    extra["publish"] = collect_publish_posture()

    # Wider LAN/WAN network health (gateway + DNS + WAN + optional targets)
    unifi = collect_network_health()
    extra["unifi"] = unifi
    metrics["unifi_ping_ms"] = unifi.get("avg_ping_ms")
    metrics["unifi_loss_pct"] = unifi.get("avg_loss_pct")

    # Optional external SAST is out of band for this template
    extra["sast"] = "deferred"
    metrics["extra_json"] = json.dumps(extra)
    return metrics


def _default_gateway() -> str | None:
    try:
        out = subprocess.check_output(["ip", "-4", "route", "show", "default"], text=True, timeout=5)
        for part in out.split():
            if part.count(".") == 3:
                return part
    except Exception:  # noqa: BLE001
        return None
    return None


def _ping_host(host: str, count: int = 10) -> dict:
    """Return {host, ping_ms, loss_pct, ok, error?} via ping -c N."""
    try:
        out = subprocess.check_output(
            ["ping", "-c", str(count), "-W", "1", host],
            text=True,
            timeout=count + 15,
            stderr=subprocess.STDOUT,
        )
        loss = None
        avg_ms = None
        for line in out.splitlines():
            m = re.search(r"(\d+(?:\.\d+)?)% packet loss", line)
            if m:
                loss = float(m.group(1))
            m = re.search(r"rtt min/avg/max/(?:mdev|stddev) = [\d.]+/([\d.]+)/", line)
            if m:
                avg_ms = float(m.group(1))
            # BusyBox / mac alternate
            m = re.search(r"round-trip min/avg/max = [\d.]+/([\d.]+)/", line)
            if m:
                avg_ms = float(m.group(1))
        return {
            "host": host,
            "ping_ms": avg_ms,
            "loss_pct": loss if loss is not None else 100.0,
            "ok": (loss is not None and loss < 100.0),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "host": host,
            "ping_ms": None,
            "loss_pct": 100.0,
            "ok": False,
            "error": str(exc)[:160],
        }


def _resolv_nameservers() -> list[str]:
    """Prefer real upstream DNS; skip systemd-resolved stub (127.0.0.53)."""
    out: list[str] = []

    def _add(ip: str) -> None:
        if not ip or ip.count(".") != 3 or ip in out:
            return
        if ip.startswith("127."):
            return
        out.append(ip)

    try:
        # resolvectl shows upstream servers when stub resolver is in use
        r = subprocess.run(
            ["resolvectl", "dns"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                # e.g. "Link 2 (enp…): 127.0.0.1 1.1.1.1"
                if ":" not in line:
                    continue
                rhs = line.split(":", 1)[1]
                for tok in rhs.split():
                    _add(tok)
    except Exception:  # noqa: BLE001
        pass
    try:
        for line in Path("/etc/resolv.conf").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("nameserver "):
                _add(line.split()[1])
    except Exception:  # noqa: BLE001
        pass
    return out[:3]


def collect_network_health() -> dict:
    """Wider LAN/WAN ICMP health + optional UniFi controller API snapshot.

    Env:
      ALFRED_UNIFI_GATEWAY — override default gateway IP
      ALFRED_UNIFI_TARGETS — comma-separated LAN hosts (APs, switches, NAS, printer)
      ALFRED_WAN_TARGETS — comma-separated WAN probes (default ``1.1.1.1,8.8.8.8``;
                           set empty to disable)
      ALFRED_UNIFI_PING_COUNT — packets per host (default 10)
      ALFRED_UNIFI_API_BASE / ALFRED_UNIFI_API_KEY — controller API (optional)
      ALFRED_UNIFI_SITE — classic site name (default ``default``)
      ALFRED_UNIFI_API_VERIFY_TLS — set 1 to verify TLS (default off)
    """
    count = int(os.environ.get("ALFRED_UNIFI_PING_COUNT", "10") or "10")
    count = max(3, min(count, 30))
    gateway = (os.environ.get("ALFRED_UNIFI_GATEWAY") or "").strip() or _default_gateway()
    lan_extras = [
        h.strip()
        for h in (os.environ.get("ALFRED_UNIFI_TARGETS") or "").split(",")
        if h.strip()
    ]
    wan_raw = os.environ.get("ALFRED_WAN_TARGETS")
    if wan_raw is None:
        wan_extras = ["1.1.1.1", "8.8.8.8"]
    else:
        wan_extras = [h.strip() for h in wan_raw.split(",") if h.strip()]

    # Role map for digest labels
    roles: dict[str, str] = {}
    ordered: list[str] = []

    def _add(host: str, role: str) -> None:
        if not host or host in roles:
            return
        roles[host] = role
        ordered.append(host)

    if gateway:
        _add(gateway, "lan-gateway")
    for dns in _resolv_nameservers():
        _add(dns, "dns")
    for h in lan_extras:
        _add(h, "lan-target")
    for h in wan_extras:
        _add(h, "wan-probe")

    if not ordered:
        return {"status": "skip", "reason": "no targets", "targets": [], "gateway": gateway}

    targets = []
    for h in ordered:
        t = _ping_host(h, count=count)
        t["role"] = roles.get(h, "other")
        targets.append(t)

    summary = classify_network_from_targets(targets, gateway=gateway)
    summary["ping_count"] = count
    summary["host_lan_ip"] = _host_lan_ipv4()
    # Controller API is additive; ICMP remains the fail-closed connectivity signal.
    summary["controller"] = (
        collect_controller_telemetry()
        if __import__('alfred_sentinel_config', fromlist=['ENABLE_CONTROLLER_API']).ENABLE_CONTROLLER_API
        else {'ok': False, 'status': 'skip', 'reason': 'controller API disabled'}
    )
    return summary


def _host_lan_ipv4() -> str | None:
    try:
        out = subprocess.check_output(
            ["ip", "-4", "-br", "addr", "show", "scope", "global"],
            text=True,
            timeout=5,
        )
        for line in out.splitlines():
            # prefer physical LAN (en*) over docker bridges
            if line.startswith("en") or line.startswith("eth") or line.startswith("wl"):
                parts = line.split()
                for p in parts:
                    if "/" in p and p.split("/")[0].count(".") == 3:
                        return p.split("/")[0]
        for line in out.splitlines():
            for p in line.split():
                if "/" in p and p.split("/")[0].count(".") == 3:
                    ip = p.split("/")[0]
                    if not ip.startswith("172."):
                        return ip
    except Exception:  # noqa: BLE001
        return None
    return None


def collect_docker_containers() -> dict:
    """Health inventory for every local Docker container (not Alfred-only)."""
    try:
        out = subprocess.check_output(
            [
                "docker",
                "ps",
                "-a",
                "--format",
                "{{.Names}}\t{{.Status}}\t{{.State}}\t{{.Ports}}",
            ],
            text=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)[:200], "containers": []}

    containers = []
    unhealthy = []
    exited = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        while len(parts) < 4:
            parts.append("")
        name, status, state, ports = parts[0], parts[1], parts[2], parts[3]
        st = (status or "").lower()
        health = "none"
        if "(healthy)" in st:
            health = "healthy"
        elif "(unhealthy)" in st:
            health = "unhealthy"
        elif "(health: starting)" in st:
            health = "starting"
        row = {
            "name": name,
            "status": status,
            "state": state or ("running" if st.startswith("up") else "unknown"),
            "health": health,
            "ports": ports or "",
            "ok": st.startswith("up") and health != "unhealthy",
        }
        containers.append(row)
        if health == "unhealthy":
            unhealthy.append(name)
        if state == "exited" or st.startswith("exited"):
            exited.append(name)

    running = sum(1 for c in containers if str(c.get("status", "")).lower().startswith("up"))
    return {
        "count": len(containers),
        "running": running,
        "unhealthy": unhealthy,
        "exited": exited,
        "containers": containers,
    }


def collect_publish_posture() -> dict:
    """Hard facts: host listeners + Docker published ports + DOCKER-USER summary."""
    listeners: list[dict] = []
    try:
        out = subprocess.check_output(["ss", "-ltn"], text=True, timeout=10)
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 4:
                continue
            local = parts[3]
            if ":" not in local:
                continue
            addr, _, port_s = local.rpartition(":")
            try:
                port = int(port_s)
            except ValueError:
                continue
            scope = (
                "loopback"
                if addr in {"127.0.0.1", "[::1]"}
                else "lan-or-all"
                if addr in {"0.0.0.0", "*", "[::]"}
                else "specific"
            )
            listeners.append({"addr": addr, "port": port, "scope": scope, "local": local})
    except Exception as exc:  # noqa: BLE001
        listeners = [{"error": str(exc)[:160]}]

    published: list[dict] = []
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
            text=True,
            timeout=20,
        )
        for line in out.splitlines():
            if "\t" not in line:
                continue
            name, ports = line.split("\t", 1)
            if not ports.strip():
                continue
            # e.g. 0.0.0.0:4000->4000/tcp, 127.0.0.1:11434->11434/tcp
            for m in re.finditer(
                r"(?P<bind>0\.0\.0\.0|127\.0\.0\.1|\[::\]|\[::1\]):(?P<host>\d+)->(?P<ctr>\d+)/(?P<proto>\w+)",
                ports,
            ):
                published.append(
                    {
                        "container": name,
                        "bind": m.group("bind"),
                        "host_port": int(m.group("host")),
                        "container_port": int(m.group("ctr")),
                        "proto": m.group("proto"),
                        "lan_reachable": m.group("bind") in {"0.0.0.0", "[::]"},
                    }
                )
    except Exception as exc:  # noqa: BLE001
        published = [{"error": str(exc)[:160]}]

    docker_user: list[str] = []
    try:
        out = subprocess.check_output(
            ["sudo", "-n", "iptables", "-L", "DOCKER-USER", "-n", "-v"],
            text=True,
            timeout=10,
            stderr=subprocess.STDOUT,
        )
        for line in out.splitlines():
            if "dpt:" in line or "multiport" in line or "DROP" in line or "RETURN" in line:
                docker_user.append(" ".join(line.split()))
    except Exception as exc:  # noqa: BLE001
        docker_user = [f"unavailable:{exc.__class__.__name__}"]

    return {
        "host_lan_ip": _host_lan_ipv4(),
        "listeners": listeners[:80],
        "docker_published": published,
        "docker_user_rules": docker_user[:40],
    }



# Back-compat alias (older callers / notes)
collect_unifi = collect_network_health
