#!/usr/bin/env python3
"""Alfred nightly Sentinel — thin orchestrator (public template).

Modules live in ./lib/. Configure via environment — see SETUP.md and .env.example.
Never git push from Sentinel. Respect MAX_LOADED=1 + flock.
"""
from __future__ import annotations

import fcntl
import json
import sys
import time
import urllib.error
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LIB = _HERE / "lib"
if _LIB.is_dir() and str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import alfred_telemetry as telemetry  # noqa: E402
from alfred_memory_rubric import utc_now_iso  # noqa: E402
from alfred_sentinel_prompts import (  # noqa: E402
    SECURITY_EMPTY_LINE,
    SECURITY_SYSTEM,
    STABILITY_SYSTEM,
    build_security_user,
    build_stability_user,
)
from alfred_sentinel_runtime import (  # noqa: E402
    acquire_lock,
    flush_models,
    litellm_chat_safe,
    load_master_key,
    log,
)
from alfred_sentinel_collect import collect_host_metrics  # noqa: E402
from alfred_sentinel_security import (  # noqa: E402
    concrete_security_risks,
    format_security_facts_md,
)
from alfred_sentinel_findings import baseline_rollup, findings_from_metrics  # noqa: E402
from alfred_sentinel_memory import memory_stage4  # noqa: E402
from alfred_sentinel_digest import (  # noqa: E402
    build_coached_prompts,
    mail_digest,
    monthly_model_survey,
    should_run_monthly_model_survey,
    write_morning_digest,
)
from alfred_sentinel_ops import (  # noqa: E402
    maybe_monday_performance_mail,
    prune_digests,
    run_backups,
    spawn_sunday_eval_matrix,
)


def main() -> int:
    started = time.time()
    day = datetime.now().strftime("%Y-%m-%d")
    models_invoked: list[str] = []
    lock_fh = acquire_lock(600)
    conn = telemetry.connect()
    telemetry.init_schema(conn)
    cur = conn.execute(
        "INSERT INTO runs (started_at, status, trigger, notes) VALUES (?, 'running', 'cron', ?)",
        (utc_now_iso(), "alfred-sentinel"),
    )
    run_id = cur.lastrowid
    conn.commit()
    status = "ok"
    notes_parts: list[str] = []
    duration = 0.0
    try:
        metrics = collect_host_metrics()
        conn.execute(
            "INSERT INTO telemetry_metrics (run_id, captured_at, gpu_temp_c, cpu_temp_c, vram_used_mb, "
            "vram_total_mb, ram_used_mb, ram_total_mb, disk_smart_json, unifi_ping_ms, unifi_loss_pct, extra_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                run_id,
                metrics["captured_at"],
                metrics["gpu_temp_c"],
                metrics["cpu_temp_c"],
                metrics["vram_used_mb"],
                metrics["vram_total_mb"],
                metrics["ram_used_mb"],
                metrics["ram_total_mb"],
                metrics["disk_smart_json"],
                metrics["unifi_ping_ms"],
                metrics["unifi_loss_pct"],
                metrics["extra_json"],
            ),
        )
        conn.commit()
        new_findings = findings_from_metrics(conn, run_id, metrics)
        baselines = baseline_rollup(conn)

        master_key = load_master_key()
        security_notes = ""
        reasoner_notes = ""
        model_survey = ""
        if master_key:
            extra_obj = json.loads(metrics.get("extra_json") or "{}")
            security_facts_md = format_security_facts_md(extra_obj)
            security_ctx = {
                "services": extra_obj.get("services"),
                "network": extra_obj.get("unifi"),
                "docker": {
                    "count": (extra_obj.get("docker") or {}).get("count"),
                    "running": (extra_obj.get("docker") or {}).get("running"),
                    "unhealthy": (extra_obj.get("docker") or {}).get("unhealthy"),
                    "exited": (extra_obj.get("docker") or {}).get("exited"),
                },
                "publish": extra_obj.get("publish"),
                "findings_new": new_findings,
                "facts_markdown_already_in_digest": True,
            }
            stability_ctx = {
                "baselines": baselines,
                "disks": extra_obj.get("disks"),
                "smart": extra_obj.get("smart"),
                "gpu_temp_c": metrics.get("gpu_temp_c"),
                "cpu_temp_c": metrics.get("cpu_temp_c"),
                "vram_used_mb": metrics.get("vram_used_mb"),
                "vram_total_mb": metrics.get("vram_total_mb"),
                "ram_used_mb": metrics.get("ram_used_mb"),
                "ram_total_mb": metrics.get("ram_total_mb"),
                "services": extra_obj.get("services"),
                "docker": extra_obj.get("docker"),
                "network": {
                    "status": (extra_obj.get("unifi") or {}).get("status"),
                    "lan_ok": (extra_obj.get("unifi") or {}).get("lan_ok"),
                    "wan_ok": (extra_obj.get("unifi") or {}).get("wan_ok"),
                    "avg_ping_ms": metrics.get("unifi_ping_ms"),
                    "avg_loss_pct": metrics.get("unifi_loss_pct"),
                    "targets": (extra_obj.get("unifi") or {}).get("targets"),
                    "controller": (extra_obj.get("unifi") or {}).get("controller"),
                },
                "findings_new": new_findings,
            }
            risks = concrete_security_risks(extra_obj)
            if not risks:
                security_notes = (
                    security_facts_md + "\n\n### Analyst note\n\n" + SECURITY_EMPTY_LINE
                )
                notes_parts.append("security:facts-only")
            else:
                try:
                    security_llm = litellm_chat_safe(
                        master_key,
                        "alfred-security",
                        build_security_user(security_ctx),
                        system=SECURITY_SYSTEM,
                    )
                    models_invoked.append("alfred-security")
                    security_notes = (
                        security_facts_md
                        + "\n\n### Analyst note (model)\n\n"
                        + (security_llm or "").strip()
                    )
                except Exception as exc:  # noqa: BLE001
                    security_notes = security_facts_md + f"\n\n_soft-fail analyst note: {exc}_"
                    notes_parts.append(f"security:{exc}")
            notes_parts.append("vram:single-resident-swap")
            try:
                reasoner_notes = litellm_chat_safe(
                    master_key,
                    "alfred-reasoner",
                    build_stability_user(stability_ctx),
                    system=STABILITY_SYSTEM,
                )
                models_invoked.append("alfred-reasoner")
            except Exception as exc:  # noqa: BLE001
                reasoner_notes = f"_soft-fail: {exc}_"
                notes_parts.append(f"reasoner:{exc}")

            try:
                mem = memory_stage4(master_key)
                if mem.get("chunks_evaluated"):
                    models_invoked.append("alfred-reasoner")
                notes_parts.append(
                    f"memory:eval={mem.get('chunks_evaluated', 0)}"
                    f"/pruned={mem.get('chunks_pruned', 0)}"
                    f"/silver={mem.get('silver_pinned', 0)}"
                )
            except Exception as exc:  # noqa: BLE001
                log(f"warn: memory_stage4 soft-fail: {exc}")
                mem = {
                    "pending_review_swept": 0,
                    "chunks_evaluated": 0,
                    "chunks_pruned": 0,
                    "silver_pinned": 0,
                    "gold_ratified": 0,
                    "gold_staged": 0,
                    "promotion_blocks": [],
                    "domain_tag_reviewed": 0,
                    "domain_tag_applied": 0,
                    "domain_tag_proposed_new": 0,
                    "domain_tag_failed": 0,
                    "domain_tag_digest": f"_soft-fail memory stage4: {exc}_",
                }
                notes_parts.append(f"memory:{exc}")

            if should_run_monthly_model_survey(day):
                try:
                    model_survey = monthly_model_survey(master_key, day)
                    models_invoked.append("alfred-reasoner")
                    notes_parts.append("monthly-model-survey:ok")
                except Exception as exc:  # noqa: BLE001
                    model_survey = f"_Monthly model survey soft-fail: {exc}_"
                    notes_parts.append(f"monthly-model-survey:{exc}")
            else:
                model_survey = "_Skipped — next run on the 1st (recommend only; never auto-pull)._"
        else:
            mem = {
                "pending_review_swept": 0,
                "chunks_evaluated": 0,
                "chunks_pruned": 0,
                "silver_pinned": 0,
                "gold_ratified": 0,
                "gold_staged": 0,
                "promotion_blocks": [],
                "domain_tag_reviewed": 0,
                "domain_tag_applied": 0,
                "domain_tag_proposed_new": 0,
                "domain_tag_failed": 0,
                "domain_tag_digest": "_skipped — no LiteLLM master key_",
            }
            model_survey = "_skipped — no LiteLLM master key_"
            notes_parts.append("no-litellm-key")

        conn.execute(
            "INSERT INTO memory_compaction_log (run_id, compacted_at, chunks_evaluated, chunks_pruned, "
            "silver_pinned, gold_ratified, gold_staged, pending_review_swept, details_json) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                run_id,
                utc_now_iso(),
                mem.get("chunks_evaluated", 0),
                mem.get("chunks_pruned", 0),
                mem.get("silver_pinned", 0),
                mem.get("gold_ratified", 0),
                mem.get("gold_staged", 0),
                mem.get("pending_review_swept", 0),
                json.dumps(
                    {
                        "promotion_count": len(mem.get("promotion_blocks") or []),
                        "domain_tag_reviewed": mem.get("domain_tag_reviewed", 0),
                        "domain_tag_applied": mem.get("domain_tag_applied", 0),
                        "domain_tag_proposed_new": mem.get("domain_tag_proposed_new", 0),
                        "domain_tag_failed": mem.get("domain_tag_failed", 0),
                    }
                ),
            ),
        )
        conn.commit()

        coached = build_coached_prompts(
            master_key if master_key else None,
            new_findings,
            metrics,
            security_notes,
            reasoner_notes,
        )
        digest_path = write_morning_digest(
            day,
            metrics,
            new_findings,
            baselines,
            security_notes,
            reasoner_notes,
            mem,
            coached_prompts=coached,
            model_survey=model_survey,
        )
        log(f"digest: {digest_path}")
        mail_status = mail_digest(digest_path)
        notes_parts.append(f"mail:{mail_status}")
        log(f"mail: {mail_status}")

        backup_notes = run_backups()
        notes_parts.append(backup_notes)
        log(f"backups: {backup_notes}")

        pruned = prune_digests()
        notes_parts.append(f"digest_pruned:{pruned}")

        try:
            tprune = telemetry.prune_retention(conn)
            notes_parts.append(
                "telemetry_pruned:"
                f"m={tprune.get('metrics_deleted', 0)}/"
                f"f={tprune.get('resolved_findings_deleted', 0)}/"
                f"r={tprune.get('runs_deleted', 0)}"
            )
            log(f"telemetry prune: {tprune}")
        except Exception as exc:  # noqa: BLE001
            notes_parts.append(f"telemetry_prune:{exc}")
            log(f"warn: telemetry prune soft-fail: {exc}")

        flush_models()
    except Exception as exc:  # noqa: BLE001
        status = "error"
        notes_parts.append(f"error:{exc}")
        log(f"FAIL: {exc}")
    finally:
        ended = utc_now_iso()
        duration = round(time.time() - started, 1)
        conn.execute(
            "UPDATE runs SET ended_at=?, duration_sec=?, status=?, models_invoked=?, notes=? WHERE id=?",
            (ended, duration, status, json.dumps(models_invoked), " | ".join(notes_parts)[:4000], run_id),
        )
        conn.commit()
        conn.close()
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        lock_fh.close()
    try:
        mon = maybe_monday_performance_mail()
        log(f"eval-matrix monday: {mon}")
    except Exception as exc:  # noqa: BLE001
        log(f"eval-matrix monday error: {exc}")
    if status == "ok":
        try:
            sun = spawn_sunday_eval_matrix()
            log(f"eval-matrix sunday: {sun}")
        except Exception as exc:  # noqa: BLE001
            log(f"eval-matrix sunday error: {exc}")
    log(f"DONE status={status} run_id={run_id} duration={duration}s")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
