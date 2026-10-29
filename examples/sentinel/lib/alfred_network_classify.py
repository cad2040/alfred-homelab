"""Pure ICMP network status + finding-kind helpers (unit-testable).

Used by alfred-sentinel collect_network_health / findings_from_metrics.
"""
from __future__ import annotations

from typing import Any


def classify_network_from_targets(
    targets: list[dict[str, Any]],
    *,
    gateway: str | None = None,
) -> dict[str, Any]:
    """Compute status / avgs from already-pinged target dicts.

    Each target: {host, ok, ping_ms?, loss_pct?, role}.
    Roles: lan-gateway | dns | lan-target | wan-probe | other.
    """
    ping_vals = [
        t["ping_ms"] for t in targets if isinstance(t.get("ping_ms"), (int, float))
    ]
    loss_vals = [
        t["loss_pct"] for t in targets if isinstance(t.get("loss_pct"), (int, float))
    ]
    lan = [t for t in targets if t.get("role") in {"lan-gateway", "dns", "lan-target"}]
    wan = [t for t in targets if t.get("role") == "wan-probe"]
    lan_ok = all(t.get("ok") for t in lan) if lan else False
    wan_ok: bool | None
    if not wan:
        wan_ok = None
    else:
        wan_ok = any(t.get("ok") for t in wan)
    if not lan:
        status = "skip"
    elif not lan_ok:
        status = "degraded"
    elif wan and wan_ok is False:
        status = "wan-degraded"
    else:
        status = "ok"
    return {
        "status": status,
        "gateway": gateway,
        "targets": targets,
        "lan_ok": lan_ok,
        "wan_ok": wan_ok,
        "avg_ping_ms": round(sum(ping_vals) / len(ping_vals), 3) if ping_vals else None,
        "avg_loss_pct": round(sum(loss_vals) / len(loss_vals), 2) if loss_vals else None,
    }


def network_finding_kinds(unifi: dict[str, Any]) -> list[str]:
    """Return finding fingerprints that findings_from_metrics would raise.

    Order matches alfred-sentinel.py (loss first, then degraded, then wan-degraded).
    """
    kinds: list[str] = []
    loss = unifi.get("avg_loss_pct")
    if isinstance(loss, (int, float)) and loss >= 5.0:
        kinds.append("unifi-loss-high")
    elif unifi.get("status") == "degraded":
        kinds.append("unifi-unreachable")
    elif unifi.get("status") == "wan-degraded":
        kinds.append("wan-unreachable")
    return kinds
