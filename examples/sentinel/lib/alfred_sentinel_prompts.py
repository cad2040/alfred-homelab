"""Sentinel digest LLM prompt SoT (security + stability).

Imported by alfred-sentinel.py (public template).
Keep hard rules here — do not duplicate inline in the orchestrator.
"""
from __future__ import annotations

import json
from typing import Any

SECURITY_EMPTY_LINE = "No additional security findings beyond the facts tables."


def chat_content_looks_broken(text: str) -> bool:
    """Detect ChatML / template echo (Foundation-Sec via Ollama)."""
    if not text or not str(text).strip():
        return True
    t = str(text)
    markers = ("<|im_start|>", "<|im_end|>", "<|endoftext|>")
    hits = sum(t.count(m) for m in markers)
    if hits >= 2:
        return True
    if hits >= 1 and len(
        t.replace("<|im_start|>", "").replace("<|im_end|>", "").strip()
    ) < 40:
        return True
    return False


SECURITY_SYSTEM = (
    "You are a terse network security analyst. Hard facts only. "
    "Never pad. Never discuss disks/SMART. Never invent credential audits "
    "or secret scans. Never recommend 'ongoing monitoring'."
)

STABILITY_SYSTEM = (
    "Host + LAN reliability engineer for a home lab (AI stack, containers, LAN controller). "
    "Cover disks/SMART/thermals/Docker AND network (ICMP fail-closed + UniFi "
    "controller API snapshot). Ground every claim in telemetry JSON. "
    "No firewall/DOCKER-USER/bind-exposure/secrets essays — Security owns those. "
    "Never invent UniFi metrics or historical 3σ claims without data."
)


def build_security_user(security_ctx: dict[str, Any], *, max_chars: int = 5500) -> str:
    """User prompt for alfred-security analyst note under facts tables."""
    return (
        "You are appending a **short analyst note** under a FACTS table "
        "that already lists publish posture, DOCKER-USER, HTTP checks, "
        "LAN/WAN reachability, and all Docker container health.\n\n"
        "HARD RULES:\n"
        "- Use ONLY facts present in the telemetry JSON / concrete-risks list.\n"
        "- Do NOT invent credential audits, secret scans, or 'ongoing monitoring' advice.\n"
        "- Do NOT discuss disk %, SMART, drive temp, or filesystem fill.\n"
        "- Do NOT restate the entire facts table.\n"
        "- If concrete risks list is empty/none: reply with EXACTLY one line and NOTHING else:\n"
        f"  `{SECURITY_EMPTY_LINE}`\n"
        "  (No bullets, no restating publish/DOCKER-USER/HTTP/LAN facts.)\n"
        "- Otherwise: ≤6 bullets, each citing a specific host_port/container/host "
        "from concrete risks — do not invent new risk classes.\n\n"
        f"Telemetry:\n{json.dumps(security_ctx)[:max_chars]}"
    )


def build_stability_user(stability_ctx: dict[str, Any], *, max_chars: int = 9000) -> str:
    """User prompt for alfred-reasoner Stability pass (host + UniFi network assessment)."""
    return (
        "You are writing the **Stability pass** for Alfred's morning digest.\n\n"
        "## Part A — Host reliability (brief)\n"
        "Scope: disk capacity + SMART; GPU/CPU thermal + VRAM/RAM vs baselines; "
        "**all Docker containers** availability/health (not just Alfred HTTP probes).\n"
        "Call out: mounts ≥80% used, SMART non-PASSED, unhealthy/exited containers, "
        "thermal/VRAM pressure.\n"
        "OUT OF SCOPE: firewall policy, DOCKER-USER, bind exposure, secrets "
        "(Security owns those).\n\n"
        "## Part B — Comprehensive Network Telemetry Health Assessment\n"
        "Use `network` in the telemetry JSON. ICMP is the **fail-closed** connectivity "
        "signal. When `network.controller.ok` is true, treat controller fields as the "
        "authoritative UniFi metric surface for this run "
        "(already collected — do **not** invent endpoints or values).\n\n"
        "### B1 — Metric inventory (acknowledge only)\n"
        "List the endpoints actually present under "
        "`network.controller.assessment.endpoints_collected` (or state controller skipped). "
        "Do not claim you queried other `/stat/*` paths.\n\n"
        "### B2 — Anomaly detection (facts only)\n"
        "From ICMP targets + controller console/health/devices/alerts/assessment:\n"
        "a) System health — WAN/WWW/WLAN/LAN subsystem status, offline devices, "
        "disconnected APs, hasInternet.\n"
        "b) Resource utilisation — gateway/AP CPU/mem/temp **snapshots** "
        "(≥75% CPU, ≥85% mem, ≥80°C, overheating). Say snapshot — no 'sustained 60m' "
        "unless a duration field exists.\n"
        "c) Traffic / capacity — AP client density, uplink_speed if present, "
        "WWW latency/xput if present. No fabricated interface saturation counters.\n"
        "d) Client anomalies — only if reflected in controller alerts / sta counts; "
        "do not invent unauthorized MACs.\n"
        "e) Security *signals* — only controller alerts already listed "
        "(reliability/IDS-ish strings in alerts). No policy redesign.\n\n"
        "### B3 — Capacity planning\n"
        "From AP client counts, CPU/mem/temp, uplink_speed, WWW xput: note headroom "
        "or pressure. Recommend redistribute/firmware/hardware **only** when grounded "
        "in those facts. If firmware compatibility is unknown, say so.\n\n"
        "### B4 — Network Health Score (NHS)\n"
        "Start from `network.controller.assessment.network_health_score` and buckets "
        "when present (deterministic snapshot). Then:\n"
        "- Apply ICMP adjustments you can justify: LAN loss ≥5% or lan_ok=false → "
        "state a −10..−25 traffic/system impact; WAN all-fail → −15..−30; "
        "healthy ICMP with no controller → score 'ICMP-only / controller skipped'.\n"
        "- Report final **NHS 0–100**, bucket breakdown, and a one-sentence method note. "
        "Never claim 3σ historical anomaly without series data.\n\n"
        "### B5 — Grounded recommendations\n"
        "For each flagged anomaly: one **low-effort** check and optionally one "
        "**higher-investment** upgrade. Verifiable via UniFi UI/API or on-box ICMP. "
        "If external context is required, acknowledge the gap.\n\n"
        "## Reply shape (markdown)\n"
        "1. **Host** — short bullets/table for disk/SMART/thermals/Docker only.\n"
        "2. **Network executive summary** — NHS + top ≤3 concerns.\n"
        "3. **Metric inventory** — collected endpoints / skip reason.\n"
        "4. **Anomalies** — categorical bullets citing concrete fields.\n"
        "5. **Capacity** — headroom / pressure from facts.\n"
        "6. **Recommendations** — prioritised, grounded.\n"
        "Be concise. Prefer tables/bullets. No motivational fluff.\n\n"
        f"Telemetry:\n{json.dumps(stability_ctx)[:max_chars]}"
    )
