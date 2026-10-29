"""Deterministic security facts + concrete-risk derivation for Sentinel."""
from __future__ import annotations

def concrete_security_risks(extra: dict) -> list[str]:
    """Fact-derived risks only. Empty means the analyst note can be skipped."""
    pub = (extra.get("publish") or {}).get("docker_published") or []
    rules = (extra.get("publish") or {}).get("docker_user_rules") or []
    docker = extra.get("docker") or {}
    net = extra.get("unifi") or {}
    risks: list[str] = []
    for p in pub:
        if p.get("lan_reachable") and p.get("host_port") in {11434, 8000}:
            risks.append(
                f"CRITICAL: `{p.get('container')}` publishes Ollama/Chroma-class port "
                f"{p.get('host_port')} on `{p.get('bind')}` (should be loopback-only)."
            )
    for name, status in (extra.get("services") or {}).items():
        if status != "ok":
            risks.append(f"HIGH: HTTP check failed for `{name}` → {status}")
    for name in docker.get("unhealthy") or []:
        risks.append(f"HIGH: container unhealthy: `{name}`")
    if net.get("status") in {"degraded", "wan-degraded"}:
        risks.append(f"HIGH: network status `{net.get('status')}` (see Network health).")
    if any(str(r).startswith("unavailable") for r in rules):
        risks.append("MEDIUM: could not read DOCKER-USER rules (sudo/iptables).")
    return risks


def format_security_facts_md(extra: dict) -> str:
    """Deterministic security section — hard facts only (no LLM fluff).

    Network and Docker tables stay in the digest body. This pass does
    not repeat them.
    """
    lines = [
        "_Facts collected on-host (not model prose)._",
        "",
        "### Publish posture (Docker)",
        "",
        "| Container | Bind | Host port | Container port | LAN-reachable |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    pub = (extra.get("publish") or {}).get("docker_published") or []
    if not pub:
        lines.append("| — | — | — | — | none |")
    for p in pub:
        if p.get("error"):
            lines.append(f"| error | {p['error']} | | | |")
            continue
        lines.append(
            f"| `{p.get('container')}` | `{p.get('bind')}` | {p.get('host_port')} | "
            f"{p.get('container_port')} | {'yes' if p.get('lan_reachable') else 'no'} |"
        )

    lines += [
        "",
        "### DOCKER-USER (iptables summary)",
        "",
    ]
    rules = (extra.get("publish") or {}).get("docker_user_rules") or []
    if not rules:
        lines.append("_No DOCKER-USER rules collected._")
    else:
        for r in rules:
            lines.append(f"- `{r}`")

    lines += [
        "",
        "### HTTP surface checks",
        "",
    ]
    for name, status in sorted((extra.get("services") or {}).items()):
        lines.append(f"- `{name}`: **{status}**")

    lines += [
        "",
        "_Network health and the full Docker table are above. Not repeated here._",
    ]

    risks = concrete_security_risks(extra)
    lines += ["", "### Concrete risks (fact-derived)", ""]
    if risks:
        lines.extend(f"- {r}" for r in risks)
    else:
        lines.append("- No concrete security risks identified from this telemetry.")
    return "\n".join(lines)
