"""Morning digest, coached prompts, monthly model survey, mail helper."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from alfred_memory_rubric import dedupe_promotion_blocks
from alfred_controller_api import format_controller_digest_lines
from alfred_sentinel_config import (
    DIGEST_DIR,
    LITELLM_CONFIG,
    OLLAMA,
    STAGED_MODEL_UPGRADES,
)
from alfred_sentinel_runtime import http_json, litellm_chat_safe, log

def _domain_for_finding(title: str) -> str:
    t = title.lower()
    if "disk" in t or "smart" in t or "free space" in t:
        return "host-disk"
    if "unifi" in t or "lan" in t or "network" in t or "gateway" in t:
        return "docker-ufw"
    if "vram" in t or "gpu" in t:
        return "vram-runtime"
    if any(x in t for x in ("ollama", "chroma", "litellm", "mcpo", "service")):
        return "vram-runtime"
    return "docker-ufw"


def _enrich_finding_detail(title: str, extra: dict) -> str:
    """Attach concrete telemetry to a finding title when available."""
    disks = extra.get("disks") or {}
    for mount, info in disks.items():
        if mount and mount in title:
            used = info.get("used_pct")
            free = info.get("free_gb")
            size = info.get("size_gb") or info.get("total_gb")
            bits = [f"mount={mount}"]
            if used is not None:
                bits.append(f"used_pct={used}")
            if free is not None:
                bits.append(f"free_gb={free}")
            if size is not None:
                bits.append(f"size_gb={size}")
            return ", ".join(bits)
    unifi = extra.get("unifi") or {}
    if any(x in title.lower() for x in ("unifi", "lan", "gateway", "network")):
        return (
            f"gateway={unifi.get('gateway')}, "
            f"avg_ping_ms={unifi.get('avg_ping_ms')}, "
            f"avg_loss_pct={unifi.get('avg_loss_pct')}, "
            f"status={unifi.get('status')}"
        )
    vram = extra.get("vram") or {}
    if any(x in title.lower() for x in ("vram", "gpu")):
        return (
            f"vram_used_mb={vram.get('used_mb') or extra.get('vram_used_mb')}, "
            f"vram_total_mb={vram.get('total_mb') or extra.get('vram_total_mb')}"
        )
    return ""


def _mature_coach_block(issue: dict) -> str:
    """Paste-ready Coach this Prompt with context, outcome, and confirm steps."""
    domain = issue["domain"]
    title = issue["title"]
    detail = (issue.get("detail") or "").strip() or title
    context = (issue.get("context") or "").strip() or (
        "Morning Sentinel telemetry on the lab host. "
        "Treat as advisory until confirmed on-box."
    )
    outcome = (issue.get("desired_outcome") or "").strip() or (
        f"Confirm whether '{title}' is a real risk, then either remediate safely "
        "or document why it is acceptable — without inventing credentials or "
        "opening WAN publishes."
    )
    confirm = (issue.get("confirm_steps") or "").strip() or (
        "1) Re-check the same metric on the host (df/findmnt/sensors/docker as relevant). "
        "2) Identify the consuming path or service before deleting anything. "
        "3) Re-run the check after any change and record before/after numbers."
    )
    return (
        "Coach this Prompt:\n"
        f"#domain:{domain}\n"
        f"## Issue\n{title}\n"
        f"## Context\n{context}\n"
        f"## Evidence (from digest telemetry)\n{detail}\n"
        f"## Desired outcome\n{outcome}\n"
        f"## How to confirm the issue is real\n{confirm}\n"
        "## Task for the coached agent\n"
        "Rewrite into an actionable host plan: diagnose → safe remediation options "
        "(prefer prune/archive over delete) → explicit do-not-touch list "
        "(live lab DB, running compose stacks unless required) → "
        "acceptance checks with exact commands and expected healthy thresholds. "
        "Do not invent credentials, API keys, or WAN publishes. Coach only — "
        "do not execute unless the human says to run next."
    )


def build_coached_prompts(
    master_key: str | None,
    new_findings: list[str],
    metrics: dict,
    security_notes: str,
    reasoner_notes: str,
) -> str:
    """Produce paste-ready Coach this Prompt blocks for concrete issues."""
    extra = json.loads(metrics.get("extra_json") or "{}")
    issues: list[dict] = []
    for title in new_findings:
        detail = _enrich_finding_detail(title, extra)
        ctx = (
            "Recurring or newly escalated Sentinel finding. "
            "Scope work to this lab host; prefer read-only confirmation first."
        )
        if "disk" in title.lower() or "/mnt/" in title:
            ctx = (
                "Disk capacity path on the lab host. Identify large trees and "
                "retention policy before any destructive prune."
            )
        issues.append(
            {
                "title": title,
                "detail": detail or title,
                "domain": _domain_for_finding(title),
                "severity": "advisory",
                "context": ctx,
                "desired_outcome": (
                    "Used% under the Sentinel threshold (typically <80%) with enough "
                    "free space for normal growth, or a documented exception with "
                    "owner + review date."
                    if ("disk" in title.lower() or "/mnt/" in title)
                    else (
                        "Root cause identified, risk rated, and either fixed with "
                        "verified acceptance checks or explicitly accepted."
                    )
                ),
                "confirm_steps": (
                    "Run `df -h <mount>` and `du -xh <mount> --max-depth=2 | sort -h | tail` "
                    "(or ncdu) to name the growth; compare to previous digest used_pct/free_gb; "
                    "confirm the mount via findmnt before any prune."
                    if ("disk" in title.lower() or "/mnt/" in title)
                    else ""
                ),
            }
        )
    # Soft issues from telemetry even when not newly escalated this run
    for mount, info in (extra.get("disks") or {}).items():
        used = info.get("used_pct")
        if isinstance(used, (int, float)) and used >= 80:
            title = f"Disk capacity pressure on {mount}"
            if not any(title in i["title"] or mount in i["title"] for i in issues):
                issues.append(
                    {
                        "title": title,
                        "detail": (
                            f"mount={mount}, used_pct={used}, "
                            f"free_gb={info.get('free_gb')}, "
                            f"size_gb={info.get('size_gb') or info.get('total_gb')}"
                        ),
                        "domain": "host-disk",
                        "severity": "advisory",
                        "context": (
                            "Disk capacity pressure on a configured mount. Prefer archive/"
                            "prune with retention awareness over blind deletes."
                        ),
                        "desired_outcome": (
                            f"{mount} used_pct < 80 with headroom for growth; "
                            "or documented retention exception."
                        ),
                        "confirm_steps": (
                            f"df -h {mount}; findmnt {mount}; identify largest dirs; "
                            "re-check used_pct after any prune."
                        ),
                    }
                )
    unifi = extra.get("unifi") or {}
    if unifi.get("status") in {"degraded", "wan-degraded"} or (
        isinstance(unifi.get("avg_loss_pct"), (int, float)) and unifi["avg_loss_pct"] >= 5
    ):
        title = "Investigate LAN/WAN network health"
        if not any(
            x in i["title"].lower() for i in issues for x in ("unifi", "lan", "wan", "network")
        ):
            issues.append(
                {
                    "title": title,
                    "detail": (
                        f"gateway={unifi.get('gateway')}, "
                        f"lan_ok={unifi.get('lan_ok')}, wan_ok={unifi.get('wan_ok')}, "
                        f"avg_ping_ms={unifi.get('avg_ping_ms')}, "
                        f"avg_loss_pct={unifi.get('avg_loss_pct')}, "
                        f"status={unifi.get('status')}"
                    ),
                    "domain": "docker-ufw",
                    "severity": "advisory",
                    "context": (
                        "Wider network path: LAN gateway/DNS/optional targets plus WAN probes. "
                        "Not limited to alfred-net. High loss or degraded status breaks "
                        "LAN Docker publishes and agent→LiteLLM sessions."
                    ),
                    "desired_outcome": (
                        "lan_ok true, wan_ok true (if probes enabled), avg_loss_pct under 5, "
                        "or root cause documented (Wi‑Fi vs switch vs ISP)."
                    ),
                    "confirm_steps": (
                        "Compare digest Network health table; ping gateway + WAN probes; "
                        "check DOCKER-USER if LAN services unreachable."
                    ),
                }
            )
    docker = extra.get("docker") or {}
    for name in (docker.get("unhealthy") or [])[:4]:
        title = f"Fix unhealthy Docker container: {name}"
        if not any(name.lower() in i["title"].lower() for i in issues):
            issues.append(
                {
                    "title": title,
                    "detail": f"container={name}, health=unhealthy",
                    "domain": "docker-ufw",
                    "severity": "critical",
                    "context": (
                        "Docker container health check failed (HEALTHCHECK). "
                        "Inspect logs before restarting or recreating."
                    ),
                    "desired_outcome": f"`{name}` reports healthy (or intentional no-healthcheck).",
                    "confirm_steps": (
                        f"docker inspect --format '{{{{json .State.Health}}}}' {name}; "
                        f"docker logs --tail 80 {name}"
                    ),
                }
            )

    if not issues and not (security_notes or reasoner_notes):
        return "_No coached prompts — no concrete issues identified._"

    blocks: list[str] = []
    for idx, issue in enumerate(issues[:8], start=1):
        prompt = _mature_coach_block(issue)
        blocks.append(f"### {idx}. {issue['title']}\n\n```text\n{prompt}\n```\n")

    # Deterministic paste-ready blocks (more reliable than 7B freeform for digests).
    _ = (master_key, security_notes, reasoner_notes)
    if not blocks:
        return "_No coached prompts — no concrete issues identified._"
    return "\n".join(blocks)


def load_litellm_alias_map() -> dict[str, str]:
    """Return {alias: litellm_params.model} from live config (no secrets)."""
    try:
        import yaml  # local — venv has PyYAML

        cfg = yaml.safe_load(LITELLM_CONFIG.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        log(f"warn: litellm config read failed: {exc}")
        return {}
    out: dict[str, str] = {}
    for entry in cfg.get("model_list") or []:
        name = entry.get("model_name")
        model = (entry.get("litellm_params") or {}).get("model")
        if name and model:
            out[str(name)] = str(model)
    return out


def ollama_local_tags() -> list[str]:
    try:
        data = http_json("GET", f"{OLLAMA}/api/tags", timeout=30) or {}
        return sorted(
            str(m.get("name") or m.get("model") or "")
            for m in (data.get("models") or [])
            if m.get("name") or m.get("model")
        )
    except Exception as exc:  # noqa: BLE001
        log(f"warn: ollama tags failed: {exc}")
        return []


def should_run_monthly_model_survey(day: str) -> bool:
    """First calendar day of the month (digest day YYYY-MM-DD)."""
    try:
        return datetime.strptime(day, "%Y-%m-%d").day == 1
    except ValueError:
        return False


def monthly_model_survey(master_key: str, day: str) -> str:
    """Recommend-only OSS model upgrade survey. NEVER pulls or edits config."""
    aliases = load_litellm_alias_map()
    local = ollama_local_tags()
    inventory = {
        "litellm_aliases": aliases,
        "ollama_tags_installed": local,
        "constraints": {
            "vram": "RTX 3060 12GB",
            "max_loaded_models": 2,
            "prefer_q_quant": "Q4_K_M / Q5_K_M class when possible",
            "never_auto_pull": True,
            "human_verifies_then_pulls": True,
            "wiring_guide": "docs/guides/wire-middleware.md",
        },
        "roles": {
            "alfred-cline": "Cline XML file edits / agent coding",
            "alfred-coder": "browser / general coding chat",
            "alfred-reasoner": "Spec Kit, planning, Sentinel reasoning",
            "alfred-iot-robotics": "IoT / robotics / firmware reasoning",
            "alfred-security": "security digest / exposure review",
            "nomic-embed-text": "embeddings only",
        },
    }
    try:
        notes = litellm_chat_safe(
            master_key,
            "alfred-reasoner",
            (
                "You are Alfred's **monthly open-source model upgrade advisor**.\n"
                "HARD RULES:\n"
                "- Recommend only. NEVER instruct Alfred or the host to `ollama pull`, "
                "  docker pull, or edit LiteLLM config automatically.\n"
                "- Human will verify, pull manually, then follow docs/guides/wire-middleware.md.\n"
                "- Stay LAN-private; no cloud API keys; respect lab VRAM + MAX_LOADED=1.\n"
                "- Prefer concrete Ollama tags (or HF GGUF refs Ollama can pull).\n\n"
                "Return markdown with sections:\n"
                "1. Current alias map (brief)\n"
                "2. Keep as-is (with one-line why)\n"
                "3. Optional upgrades (table: role | current | candidate tag | why | "
                "   VRAM risk | priority P1/P2/P3)\n"
                "4. Do-not-recommend list (too big / wrong fit)\n"
                "5. Human next steps (pull command template + 'then run Coach wire prompt')\n\n"
                f"Inventory JSON:\n{json.dumps(inventory)[:7000]}"
            ),
            system=(
                "Conservative local-LLM lab advisor. Never auto-pull. "
                "Be specific; inventing unavailable tags is worse than saying unknown."
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return f"_Monthly model survey soft-fail: {exc}_"

    # Persist beyond digest prune window
    try:
        STAGED_MODEL_UPGRADES.mkdir(parents=True, exist_ok=True)
        stamp = day[:7]  # YYYY-MM
        path = STAGED_MODEL_UPGRADES / f"{stamp}-survey.md"
        path.write_text(
            f"# Alfred monthly model survey {day}\n\n"
            f"_Recommend only — no auto-pull._\n\n"
            f"{notes.rstrip()}\n",
            encoding="utf-8",
        )
        log(f"model-survey staged: {path}")
        footer = f"\n\n_Staged copy: `{path}`_"
    except Exception as exc:  # noqa: BLE001
        footer = f"\n\n_Warn: could not stage survey file: {exc}_"
    return notes.rstrip() + footer


def write_morning_digest(
    day: str,
    metrics: dict,
    new_findings: list[str],
    baselines: str,
    security_notes: str,
    reasoner_notes: str,
    mem: dict,
    coached_prompts: str = "",
    model_survey: str = "",
) -> Path:
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGEST_DIR / f"{day}.md"
    extra = json.loads(metrics.get("extra_json") or "{}")

    disk_lines = [
        "## Disk capacity",
        "",
        "| Mount | Device | Used | Free | Total |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for mount in __import__('alfred_sentinel_config', fromlist=['DISK_MOUNTS']).DISK_MOUNTS:
        info = (extra.get("disks") or {}).get(mount) or {}
        if "error" in info:
            disk_lines.append(f"| `{mount}` | — | error | {info['error']} | — |")
        else:
            disk_lines.append(
                f"| `{mount}` | `{info.get('source') or '?'}` | "
                f"**{info.get('used_pct')}%** | {info.get('free_gb')} GB | {info.get('total_gb')} GB |"
            )

    smart_lines = [
        "## Disk SMART health",
        "",
        "| Mount | Device | Overall | Realloc | Pending | Uncorrectable | Temp C | Power-on h |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    smart = extra.get("smart") or {}
    if not smart:
        smart_lines = ["## Disk SMART health", "", "_No SMART data collected_"]
    for mount in __import__('alfred_sentinel_config', fromlist=['DISK_MOUNTS']).DISK_MOUNTS:
        info = smart.get(mount) or {}
        if not info:
            continue
        if info.get("error"):
            smart_lines.append(f"| `{mount}` | — | unavailable | | | | | |")
            continue
        attrs = info.get("attrs") or {}
        smart_lines.append(
            f"| `{mount}` | `{info.get('device')}` | **{info.get('overall')}** | "
            f"{attrs.get('Reallocated_Sector_Ct', '—')} | "
            f"{attrs.get('Current_Pending_Sector', '—')} | "
            f"{attrs.get('Offline_Uncorrectable', '—')} | "
            f"{attrs.get('Temperature_Celsius', '—')} | "
            f"{attrs.get('Power_On_Hours', '—')} |"
        )

    unifi = extra.get("unifi") or {}
    unifi_lines = [
        "## Network health (LAN / WAN)",
        "",
        f"- Status: **{unifi.get('status', 'unknown')}**",
        f"- Host LAN IP: `{unifi.get('host_lan_ip') or 'n/a'}`",
        f"- Gateway: `{unifi.get('gateway') or 'n/a'}`",
        f"- LAN ok: **{unifi.get('lan_ok')}** · WAN ok: **{unifi.get('wan_ok')}**",
        f"- Avg ping: **{unifi.get('avg_ping_ms')}** ms · Avg loss: **{unifi.get('avg_loss_pct')}%**",
        f"- Packets/host: {unifi.get('ping_count')}",
        "",
        "| Role | Host | Ping ms | Loss % | OK |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for t in unifi.get("targets") or []:
        unifi_lines.append(
            f"| {t.get('role')} | `{t.get('host')}` | {t.get('ping_ms')} | {t.get('loss_pct')} | "
            f"{'yes' if t.get('ok') else 'no'} |"
        )
    if not unifi.get("targets"):
        unifi_lines.append("| — | — | — | — | no targets |")
    unifi_lines += [
        "",
        "_ICMP: set `ALFRED_UNIFI_TARGETS` (LAN APs/NAS/etc.) and optionally override "
        "`ALFRED_WAN_TARGETS` (default `1.1.1.1,8.8.8.8`)._",
    ]
    unifi_lines += format_controller_digest_lines(unifi.get("controller"))

    docker = extra.get("docker") or {}
    docker_lines = [
        "## Docker containers (all)",
        "",
        f"- Total: **{docker.get('count', 0)}** · Running: **{docker.get('running', 0)}** · "
        f"Unhealthy: **{len(docker.get('unhealthy') or [])}** · "
        f"Exited: **{len(docker.get('exited') or [])}**",
        "",
        "| Name | Status | Health | Ports |",
        "| --- | --- | --- | --- |",
    ]
    for c in docker.get("containers") or []:
        docker_lines.append(
            f"| `{c.get('name')}` | {c.get('status')} | {c.get('health')} | "
            f"`{(c.get('ports') or '—')[:72]}` |"
        )
    if not docker.get("containers"):
        docker_lines.append(
            f"| — | {docker.get('error') or 'none'} | — | — |"
        )

    svc = extra.get("services") or {}
    svc_bits = ", ".join(f"`{k}`={v}" for k, v in svc.items()) or "n/a"

    body = [
        f"# Alfred morning digest {day}",
        "",
        "## Host snapshot",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| GPU temp | {metrics.get('gpu_temp_c')} C |",
        f"| VRAM | {metrics.get('vram_used_mb')} / {metrics.get('vram_total_mb')} MB |",
        f"| RAM | {metrics.get('ram_used_mb')} / {metrics.get('ram_total_mb')} MB |",
        f"| Services | {svc_bits} |",
        "",
        *disk_lines,
        "",
        *smart_lines,
        "",
        *unifi_lines,
        "",
        *docker_lines,
        "",
        baselines,
        "",
        "## New / escalated findings",
    ]
    if new_findings:
        body.extend(f"- {t}" for t in new_findings)
    else:
        body.append("- None")
    body += [
        "",
        "## Coached prompts",
        "",
        "Paste any block into Open WebUI / Cline starting with `Coach this Prompt:` "
        "(coach only — does not execute).",
        "",
        coached_prompts or "_No coached prompts — no concrete issues identified._",
        "",
        "## Security pass",
        "",
        security_notes or "_skipped/soft-fail_",
        "",
        "## Stability pass",
        "",
        reasoner_notes or "_skipped/soft-fail_",
        "",
        "## Monthly model survey (recommend only)",
        "",
        model_survey
        or "_Skipped — runs on the 1st of each month. Never auto-pulls._",
        "",
    ]
    body += [
        "## Bronze domain tags (reasoner)",
        "",
        mem.get("domain_tag_digest")
        or "_No Bronze domain-tag reviews this run._",
        "",
        f"- reviewed: {mem.get('domain_tag_reviewed', 0)} | "
        f"applied existing: {mem.get('domain_tag_applied', 0)} | "
        f"proposed new: {mem.get('domain_tag_proposed_new', 0)} | "
        f"failed: {mem.get('domain_tag_failed', 0)}",
        "",
        "## Memory Stage 4",
        f"- pending swept: {mem.get('pending_review_swept')}",
        f"- evaluated: {mem.get('chunks_evaluated')}",
        f"- pruned: {mem.get('chunks_pruned')}",
        f"- silver: {mem.get('silver_pinned')}",
        f"- gold ratified: {mem.get('gold_ratified')}",
        f"- gold staged: {mem.get('gold_staged')}",
        f"- gold deduped (skill already in git): {mem.get('gold_deduped', 0)}",
        "",
    ]
    promo_blocks = dedupe_promotion_blocks(list(mem.get("promotion_blocks") or []))
    if promo_blocks:
        body += [
            "### Gold promotion decisions",
            "",
            "Each candidate below includes a paste-ready **apply / ignore / alter** prompt. "
            "Chroma Gold may already be ratified; git skill apply stays human-gated.",
            "",
        ]
    for block in promo_blocks:
        body.append(block)
        body.append("")
    body += [
        "## Notes",
        "- **Bronze domain tags:** existing registry hits are auto-confirmed (rollup only). "
        "Only **unique NEW** domain ids get a fenced apply/ignore/alter prompt. "
        "Never auto-merged into your domains registry.",
        "- **Gold promotions:** skipped when a matching `skills/<slug|domain>/` already exists "
        "(pinned Silver instead). Remaining candidates are human apply/ignore/alter — "
        "never git-push from Sentinel.",
        "- **Security pass:** LiteLLM alias `alfred-security` (Instruct). "
        "Reject ChatML/`<|im_start|>` junk if it reappears.",
        "- Network section = ICMP (fail-closed) + optional controller API snapshot + "
        "deterministic Controller NHS (`ALFRED_UNIFI_API_KEY` / `ALFRED_UNIFI_API_BASE`). "
        "Stability pass interprets NHS + ICMP; does not invent `/stat/*` metrics.",
        "- Stack left running after Sentinel. Digests are proposals only.",
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")
    return path


def mail_digest(path: Path) -> str:
    """Optional: set SENTINEL_MAIL_CMD to a wrapper that accepts the digest path."""
    import os

    helper = (os.environ.get("SENTINEL_MAIL_CMD") or "").strip()
    if not helper:
        return "mail-skipped"
    try:
        r = subprocess.run(
            [helper, str(path)],
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        if r.returncode == 0:
            return "sent"
        return f"fail:{(r.stderr or r.stdout or 'nonzero')[:200]}"
    except Exception as exc:  # noqa: BLE001
        return f"fail:{exc}"
