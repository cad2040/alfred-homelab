"""Optional LAN network controller telemetry for Alfred Sentinel (read-only).

Env (load from your private `.env` — never commit secrets):
  ALFRED_UNIFI_API_BASE   e.g. https://127.0.0.1:11443
  ALFRED_UNIFI_API_KEY    Integrations API key (X-API-Key)
  ALFRED_UNIFI_SITE       classic site name (default: default)
  ALFRED_UNIFI_API_VERIFY_TLS  0/false to skip self-signed verify (default)

Missing key/base => status=skip (ICMP path still runs). Soft-fail on errors.
Requires SENTINEL_ENABLE_CONTROLLER_API=1 for collectors that gate on it.
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any

GATEWAY_TYPES = {"ugw", "uxg", "ucg", "udm"}


def _truthy(val: str | None, default: bool = False) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() not in {"0", "false", "no", "off"}


def _env_config() -> dict[str, Any]:
    base = (os.environ.get("ALFRED_UNIFI_API_BASE") or "").strip().rstrip("/")
    key = (os.environ.get("ALFRED_UNIFI_API_KEY") or "").strip()
    site = (os.environ.get("ALFRED_UNIFI_SITE") or "default").strip() or "default"
    verify = _truthy(os.environ.get("ALFRED_UNIFI_API_VERIFY_TLS"), default=False)
    return {"base": base, "key": key, "site": site, "verify_tls": verify}


def _ssl_context(verify_tls: bool) -> ssl.SSLContext:
    if verify_tls:
        return ssl.create_default_context()
    return ssl._create_unverified_context()  # noqa: S323 — local self-signed controller TLS


def http_get_json(
    url: str,
    *,
    api_key: str,
    verify_tls: bool = False,
    timeout: float = 20.0,
) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "X-API-Key": api_key,
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(
        req, context=_ssl_context(verify_tls), timeout=timeout
    ) as resp:
        raw = resp.read()
        if not raw:
            return None
        ctype = (resp.headers.get("Content-Type") or "").lower()
        text = raw.decode("utf-8", errors="replace")
        if "json" not in ctype and not text.lstrip().startswith(("{", "[")):
            raise RuntimeError(f"non-json response from {url} (ctype={ctype})")
        return json.loads(text)


def _subsys(health_rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for row in health_rows:
        if row.get("subsystem") == name:
            return row
    return {}


def summarize_health(health_rows: list[dict[str, Any]]) -> dict[str, Any]:
    wan = _subsys(health_rows, "wan")
    www = _subsys(health_rows, "www")
    lan = _subsys(health_rows, "lan")
    wlan = _subsys(health_rows, "wlan")
    vpn = _subsys(health_rows, "vpn")
    return {
        "wan": {
            "status": wan.get("status"),
            "wan_ip": wan.get("wan_ip"),
            "isp_name": wan.get("isp_name") or wan.get("isp_organization"),
        },
        "www": {
            "status": www.get("status"),
            "latency": www.get("latency"),
            "speedtest_ping": www.get("speedtest_ping"),
            "xput_down": www.get("xput_down"),
            "xput_up": www.get("xput_up"),
            "speedtest_status": www.get("speedtest_status"),
        },
        "lan": {
            "status": lan.get("status"),
            "num_user": lan.get("num_user"),
            "num_sw": lan.get("num_sw"),
        },
        "wlan": {
            "status": wlan.get("status"),
            "num_user": wlan.get("num_user"),
            "num_guest": wlan.get("num_guest"),
            "num_ap": wlan.get("num_ap"),
            "num_disconnected": wlan.get("num_disconnected"),
        },
        "vpn": {
            "status": vpn.get("status"),
            "remote_user_num_active": vpn.get("remote_user_num_active"),
        },
    }


def _device_brief(dev: dict[str, Any]) -> dict[str, Any]:
    ss = dev.get("system-stats") or {}
    wan1 = dev.get("wan1") or {}
    temps = dev.get("temperatures") or []
    temp_c = None
    if isinstance(temps, list):
        for t in temps:
            if isinstance(t, dict) and t.get("value") is not None:
                temp_c = _num(t.get("value"))
                if temp_c is not None:
                    break
    out: dict[str, Any] = {
        "name": dev.get("name") or dev.get("mac"),
        "type": dev.get("type"),
        "model": dev.get("model"),
        "version": dev.get("version") or dev.get("displayable_version"),
        "state": dev.get("state"),
        "online": dev.get("state") == 1,
        "num_sta": dev.get("num_sta"),
        "uptime_sec": dev.get("uptime") or dev.get("_uptime"),
        "cpu_pct": _num(ss.get("cpu")),
        "mem_pct": _num(ss.get("mem")),
        "temp_c": temp_c,
        "overheating": bool(dev.get("overheating")),
        "tx_bytes": _num(dev.get("tx_bytes")),
        "rx_bytes": _num(dev.get("rx_bytes")),
        "satisfaction": _num(dev.get("satisfaction")),
    }
    uplink = dev.get("uplink") if isinstance(dev.get("uplink"), dict) else {}
    if uplink:
        out["uplink_speed"] = _num(uplink.get("speed"))
        out["uplink_full_duplex"] = uplink.get("full_duplex")
        out["uplink_type"] = uplink.get("type") or uplink.get("name")
    if wan1:
        out["wan1_up"] = bool(wan1.get("up"))
        out["wan1_ip"] = wan1.get("ip")
    return out


def _num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def summarize_devices(devices: list[dict[str, Any]]) -> dict[str, Any]:
    briefs = [_device_brief(d) for d in devices]
    online = [b for b in briefs if b.get("online")]
    offline = [b for b in briefs if not b.get("online")]
    gateways = [b for b in briefs if (b.get("type") or "").lower() in GATEWAY_TYPES]
    aps = [b for b in briefs if (b.get("type") or "").lower() == "uap"]
    switches = [b for b in briefs if (b.get("type") or "").lower() in {"usw", "usw-flex"}]
    return {
        "total": len(briefs),
        "online": len(online),
        "offline": [
            {"name": b["name"], "type": b["type"], "model": b["model"]} for b in offline
        ],
        "gateway": gateways[0] if gateways else None,
        "aps": [
            {
                "name": b["name"],
                "model": b["model"],
                "version": b.get("version"),
                "online": b["online"],
                "num_sta": b["num_sta"],
                "cpu_pct": b["cpu_pct"],
                "mem_pct": b["mem_pct"],
                "temp_c": b.get("temp_c"),
                "satisfaction": b.get("satisfaction"),
                "uplink_speed": b.get("uplink_speed"),
            }
            for b in aps
        ],
        "switches": [
            {
                "name": b["name"],
                "model": b["model"],
                "version": b.get("version"),
                "online": b["online"],
                "cpu_pct": b.get("cpu_pct"),
                "mem_pct": b.get("mem_pct"),
            }
            for b in switches
        ],
        "client_sta_sum": sum(
            int(b["num_sta"]) for b in briefs if isinstance(b.get("num_sta"), (int, float))
        ),
    }


def derive_alerts(
    *,
    console: dict[str, Any],
    health: dict[str, Any],
    devices: dict[str, Any],
) -> list[str]:
    alerts: list[str] = []
    if console.get("has_internet") is False:
        alerts.append("console reports hasInternet=false")
    wan_st = (health.get("wan") or {}).get("status")
    if wan_st and wan_st not in {"ok", "unknown", None}:
        alerts.append(f"WAN subsystem status={wan_st}")
    www_st = (health.get("www") or {}).get("status")
    if www_st and www_st not in {"ok", "unknown", None}:
        alerts.append(f"WWW/internet subsystem status={www_st}")
    wlan = health.get("wlan") or {}
    if isinstance(wlan.get("num_disconnected"), int) and wlan["num_disconnected"] > 0:
        alerts.append(f"{wlan['num_disconnected']} WLAN AP(s) disconnected")
    for off in devices.get("offline") or []:
        alerts.append(f"device offline: {off.get('name')} ({off.get('type')}/{off.get('model')})")
    gw = devices.get("gateway") or {}
    if gw.get("overheating"):
        alerts.append(f"gateway overheating: {gw.get('name')}")
    if gw and gw.get("wan1_up") is False:
        alerts.append(f"gateway wan1 down: {gw.get('name')}")
    for ap in devices.get("aps") or []:
        cpu = ap.get("cpu_pct")
        mem = ap.get("mem_pct")
        temp = ap.get("temp_c")
        sta = ap.get("num_sta")
        if isinstance(cpu, (int, float)) and cpu >= 75:
            alerts.append(f"AP CPU elevated (snapshot): {ap.get('name')} {cpu}%")
        if isinstance(mem, (int, float)) and mem >= 85:
            alerts.append(f"AP mem elevated (snapshot): {ap.get('name')} {mem}%")
        if isinstance(temp, (int, float)) and temp >= 80:
            alerts.append(f"AP temp high (snapshot): {ap.get('name')} {temp}°C")
        if isinstance(sta, (int, float)) and sta >= 40:
            alerts.append(f"AP client density high: {ap.get('name')} {int(sta)} sta")
    gw_cpu = gw.get("cpu_pct") if gw else None
    gw_mem = gw.get("mem_pct") if gw else None
    if isinstance(gw_cpu, (int, float)) and gw_cpu >= 75:
        alerts.append(f"gateway CPU elevated (snapshot): {gw.get('name')} {gw_cpu}%")
    if isinstance(gw_mem, (int, float)) and gw_mem >= 85:
        alerts.append(f"gateway mem elevated (snapshot): {gw.get('name')} {gw_mem}%")
    return alerts[:24]


def score_controller_assessment(
    *,
    console: dict[str, Any],
    health: dict[str, Any],
    devices: dict[str, Any],
    alerts: list[str],
    clients_active: int | None = None,
) -> dict[str, Any]:
    """Deterministic Network Health Score inputs (0–100) from collected facts only.

    Not a historical/3σ model — snapshot thresholds only. ICMP is scored separately
    by the Sentinel stability prompt when present.
    """
    deductions: list[dict[str, Any]] = []
    system_pts = 20.0
    resource_pts = 25.0
    traffic_pts = 30.0
    security_pts = 25.0  # controller reliability signals only (not firewall policy)

    if console.get("has_internet") is False:
        system_pts -= 12
        deductions.append({"bucket": "system", "delta": -12, "why": "hasInternet=false"})
    wan_st = (health.get("wan") or {}).get("status")
    if wan_st and wan_st not in {"ok", "unknown", None}:
        system_pts -= 8
        deductions.append({"bucket": "system", "delta": -8, "why": f"WAN status={wan_st}"})
    www_st = (health.get("www") or {}).get("status")
    if www_st and www_st not in {"ok", "unknown", None}:
        system_pts -= 6
        deductions.append({"bucket": "system", "delta": -6, "why": f"WWW status={www_st}"})

    offline_n = len(devices.get("offline") or [])
    if offline_n:
        d = min(20.0, 5.0 * offline_n)
        system_pts -= d
        deductions.append(
            {"bucket": "system", "delta": -d, "why": f"{offline_n} device(s) offline"}
        )
    wlan = health.get("wlan") or {}
    disc = wlan.get("num_disconnected")
    if isinstance(disc, int) and disc > 0:
        d = min(10.0, 4.0 * disc)
        system_pts -= d
        deductions.append(
            {"bucket": "system", "delta": -d, "why": f"{disc} WLAN AP(s) disconnected"}
        )

    gw = devices.get("gateway") or {}
    if gw.get("overheating"):
        resource_pts -= 12
        deductions.append({"bucket": "resource", "delta": -12, "why": "gateway overheating"})
    if gw.get("wan1_up") is False:
        traffic_pts -= 15
        deductions.append({"bucket": "traffic", "delta": -15, "why": "gateway wan1 down"})
    for label, node in [("gateway", gw), *[("AP", ap) for ap in (devices.get("aps") or [])]]:
        if not node:
            continue
        cpu = node.get("cpu_pct")
        mem = node.get("mem_pct")
        temp = node.get("temp_c")
        name = node.get("name") or label
        if isinstance(cpu, (int, float)) and cpu >= 75:
            d = 6 if cpu < 90 else 10
            resource_pts -= d
            deductions.append(
                {"bucket": "resource", "delta": -d, "why": f"{label} {name} cpu={cpu}%"}
            )
        if isinstance(mem, (int, float)) and mem >= 85:
            resource_pts -= 5
            deductions.append(
                {"bucket": "resource", "delta": -5, "why": f"{label} {name} mem={mem}%"}
            )
        if isinstance(temp, (int, float)) and temp >= 80:
            resource_pts -= 8
            deductions.append(
                {"bucket": "resource", "delta": -8, "why": f"{label} {name} temp={temp}°C"}
            )

    dense = [
        ap
        for ap in (devices.get("aps") or [])
        if isinstance(ap.get("num_sta"), (int, float)) and ap["num_sta"] >= 40
    ]
    if dense:
        d = min(12.0, 4.0 * len(dense))
        traffic_pts -= d
        deductions.append(
            {
                "bucket": "traffic",
                "delta": -d,
                "why": f"{len(dense)} AP(s) ≥40 clients (snapshot)",
            }
        )

    # Security bucket here = controller-visible reliability/security *signals* only
    if alerts:
        d = min(15.0, 2.0 * len(alerts))
        security_pts -= d
        deductions.append(
            {"bucket": "security_signals", "delta": -d, "why": f"{len(alerts)} controller alerts"}
        )

    system_pts = max(0.0, system_pts)
    resource_pts = max(0.0, resource_pts)
    traffic_pts = max(0.0, traffic_pts)
    security_pts = max(0.0, security_pts)
    total = round(system_pts + resource_pts + traffic_pts + security_pts, 1)
    return {
        "network_health_score": total,
        "max_score": 100,
        "method": "snapshot-thresholds-v1",
        "note": (
            "Controller API snapshot only — no historical 3σ. "
            "ICMP connectivity scored separately in Stability pass."
        ),
        "buckets": {
            "system_health": round(system_pts, 1),
            "resource_headroom": round(resource_pts, 1),
            "traffic_efficiency": round(traffic_pts, 1),
            "security_signals": round(security_pts, 1),
        },
        "bucket_max": {
            "system_health": 20,
            "resource_headroom": 25,
            "traffic_efficiency": 30,
            "security_signals": 25,
        },
        "deductions": deductions[:24],
        "clients_active": clients_active,
        "endpoints_collected": [
            "GET /api/system",
            "GET /proxy/network/api/s/{site}/stat/health",
            "GET /proxy/network/api/s/{site}/stat/device",
            "GET /proxy/network/api/s/{site}/stat/sta (count)",
        ],
    }


def summarize_controller_payload(
    *,
    system: dict[str, Any] | None,
    health_data: list[dict[str, Any]] | None,
    devices_data: list[dict[str, Any]] | None,
    clients_count: int | None = None,
    site: str = "default",
) -> dict[str, Any]:
    console = {
        "name": (system or {}).get("name"),
        "model": ((system or {}).get("hardware") or {}).get("shortname"),
        "has_internet": (system or {}).get("hasInternet"),
        "cloud_connected": (system or {}).get("cloudConnected"),
    }
    health = summarize_health(health_data or [])
    devices = summarize_devices(devices_data or [])
    alerts = derive_alerts(console=console, health=health, devices=devices)
    assessment = score_controller_assessment(
        console=console,
        health=health,
        devices=devices,
        alerts=alerts,
        clients_active=clients_count,
    )
    return {
        "ok": True,
        "source": "api",
        "site": site,
        "console": console,
        "health": health,
        "devices": devices,
        "clients_active": clients_count,
        "alerts": alerts,
        "assessment": assessment,
    }


def collect_controller_telemetry(
    *,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Fetch + summarize controller telemetry. Never raises — returns skip/error dict."""
    cfg = _env_config()
    if not cfg["base"] or not cfg["key"]:
        return {
            "ok": False,
            "status": "skip",
            "reason": "ALFRED_UNIFI_API_BASE/KEY not set",
        }
    base = cfg["base"]
    key = cfg["key"]
    site = cfg["site"]
    verify = cfg["verify_tls"]
    try:
        system = http_get_json(
            f"{base}/api/system", api_key=key, verify_tls=verify, timeout=timeout
        )
        health = http_get_json(
            f"{base}/proxy/network/api/s/{site}/stat/health",
            api_key=key,
            verify_tls=verify,
            timeout=timeout,
        )
        devices = http_get_json(
            f"{base}/proxy/network/api/s/{site}/stat/device",
            api_key=key,
            verify_tls=verify,
            timeout=timeout,
        )
        clients_count = None
        try:
            sta = http_get_json(
                f"{base}/proxy/network/api/s/{site}/stat/sta",
                api_key=key,
                verify_tls=verify,
                timeout=timeout,
            )
            if isinstance(sta, dict) and isinstance(sta.get("data"), list):
                clients_count = len(sta["data"])
        except Exception:  # noqa: BLE001
            clients_count = None

        health_rows = (health or {}).get("data") if isinstance(health, dict) else None
        device_rows = (devices or {}).get("data") if isinstance(devices, dict) else None
        if not isinstance(health_rows, list):
            health_rows = []
        if not isinstance(device_rows, list):
            device_rows = []
        summary = summarize_controller_payload(
            system=system if isinstance(system, dict) else {},
            health_data=health_rows,
            devices_data=device_rows,
            clients_count=clients_count,
            site=site,
        )
        summary["base"] = base
        return summary
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": "error",
            "reason": f"HTTP {exc.code}",
            "detail": str(exc.reason)[:160],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": "error",
            "reason": exc.__class__.__name__,
            "detail": str(exc)[:200],
        }


def format_controller_digest_lines(controller: dict[str, Any] | None) -> list[str]:
    """Markdown lines for morning digest (under ICMP Network health)."""
    c = controller or {}
    lines = ["", "### network controller (API)", ""]
    if not c:
        lines.append("_No controller block._")
        return lines
    if not c.get("ok"):
        lines.append(
            f"- Status: **{c.get('status', 'error')}** — `{c.get('reason', 'unknown')}`"
        )
        if c.get("detail"):
            lines.append(f"- Detail: `{c['detail']}`")
        return lines
    cons = c.get("console") or {}
    health = c.get("health") or {}
    wan = health.get("wan") or {}
    www = health.get("www") or {}
    wlan = health.get("wlan") or {}
    lan = health.get("lan") or {}
    devices = c.get("devices") or {}
    lines += [
        f"- Console: **{cons.get('name') or 'n/a'}** (`{cons.get('model') or '?'}`) · "
        f"hasInternet: **{cons.get('has_internet')}** · site `{c.get('site')}`",
        f"- WAN: status `{wan.get('status')}` · IP `{wan.get('wan_ip') or 'n/a'}` · "
        f"ISP `{wan.get('isp_name') or 'n/a'}`",
        f"- WWW: status `{www.get('status')}` · latency `{www.get('latency')}` · "
        f"speedtest ping `{www.get('speedtest_ping')}` · "
        f"xput ↓`{www.get('xput_down')}` ↑`{www.get('xput_up')}`",
        f"- WLAN: status `{wlan.get('status')}` · users **{wlan.get('num_user')}** · "
        f"APs **{wlan.get('num_ap')}** · disconnected **{wlan.get('num_disconnected')}**",
        f"- LAN: status `{lan.get('status')}` · wired users `{lan.get('num_user')}` · "
        f"switches `{lan.get('num_sw')}`",
        f"- Devices: online **{devices.get('online')}/{devices.get('total')}** · "
        f"active clients **{c.get('clients_active')}** · "
        f"AP sta sum **{devices.get('client_sta_sum')}**",
    ]
    gw = devices.get("gateway")
    if gw:
        lines.append(
            f"- Gateway: `{gw.get('name')}` online={gw.get('online')} "
            f"cpu={gw.get('cpu_pct')}% mem={gw.get('mem_pct')}% "
            f"wan1_up={gw.get('wan1_up')} oh={gw.get('overheating')}"
        )
    aps = devices.get("aps") or []
    if aps:
        lines += [
            "",
            "| AP | Model | Online | Clients | CPU % | Mem % | Temp °C | Uplink |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for ap in aps:
            lines.append(
                f"| `{ap.get('name')}` | `{ap.get('model')}` | "
                f"{'yes' if ap.get('online') else 'no'} | {ap.get('num_sta')} | "
                f"{ap.get('cpu_pct')} | {ap.get('mem_pct')} | {ap.get('temp_c')} | "
                f"{ap.get('uplink_speed') or '—'} |"
            )
    alerts = c.get("alerts") or []
    if alerts:
        lines += ["", "**Controller alerts:**"]
        for a in alerts:
            lines.append(f"- {a}")
    else:
        lines.append("- Controller alerts: none")
    assessment = c.get("assessment") or {}
    if assessment:
        buckets = assessment.get("buckets") or {}
        lines += [
            "",
            f"**Controller NHS (snapshot):** "
            f"**{assessment.get('network_health_score')}"
            f"/{assessment.get('max_score', 100)}** "
            f"· system `{buckets.get('system_health')}` · "
            f"resource `{buckets.get('resource_headroom')}` · "
            f"traffic `{buckets.get('traffic_efficiency')}` · "
            f"signals `{buckets.get('security_signals')}`",
            f"_Method: `{assessment.get('method')}` — {assessment.get('note')}_",
        ]
        ends = assessment.get("endpoints_collected") or []
        if ends:
            lines.append("- Endpoints collected: " + "; ".join(f"`{e}`" for e in ends))
    return lines
