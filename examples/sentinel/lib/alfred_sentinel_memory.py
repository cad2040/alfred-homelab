"""Bronze domain-tag + Memory Stage 4 (rubric / Gold / Silver) for Sentinel."""
from __future__ import annotations

from datetime import datetime, timezone

from alfred_memory_rubric import (
    RUBRIC_SYSTEM_PROMPT,
    digest_promotion_block,
    gold_skill_already_exists,
    parse_rubric_response,
    route_score,
    stage_gold_promotion,
    utc_now_iso,
)
from alfred_domain_tagger import (
    DOMAIN_TAG_SYSTEM_PROMPT,
    apply_suggestion_to_meta,
    build_domain_tag_user_prompt,
    digest_domain_tag_section,
    ensure_domain_line,
    known_domain_ids,
    load_known_domains,
    needs_domain_tag,
    parse_domain_tag_response,
    stage_domain_proposal,
)
from alfred_sentinel_config import BRONZE, CHROMA, EMBED_TAG, GOLD, OLLAMA
from alfred_sentinel_runtime import flush_models, http_json, litellm_chat_safe, log

def collection_id(name: str) -> str:
    cols = http_json("GET", f"{CHROMA}/collections") or []
    for c in cols:
        if c.get("name") == name:
            return c["id"]
    raise RuntimeError(f"missing collection {name}")


def get_pending_review(limit: int = 20) -> list[dict]:
    cid = collection_id(BRONZE)
    data = http_json(
        "POST",
        f"{CHROMA}/collections/{cid}/get",
        {
            "where": {"review_status": "pending-review"},
            "include": ["documents", "metadatas"],
            "limit": limit,
        },
    ) or {}
    out = []
    for i, doc, meta in zip(data.get("ids") or [], data.get("documents") or [], data.get("metadatas") or []):
        out.append({"id": i, "document": doc or "", "metadata": meta or {}})
    return out


def get_bronze_for_domain_tagging(limit: int = 12) -> list[dict]:
    """Bronze items missing a usable domain tag (use/context-driven tagging)."""
    try:
        known_ids = known_domain_ids()
    except Exception:  # noqa: BLE001
        known_ids = set()
    cid = collection_id(BRONZE)
    data = http_json(
        "POST",
        f"{CHROMA}/collections/{cid}/get",
        {
            "include": ["documents", "metadatas"],
            "limit": 80,
        },
    ) or {}
    out: list[dict] = []
    for i, doc, meta in zip(
        data.get("ids") or [],
        data.get("documents") or [],
        data.get("metadatas") or [],
    ):
        meta = meta or {}
        if not needs_domain_tag(meta, known_ids):
            continue
        out.append({"id": i, "document": doc or "", "metadata": meta})
        if len(out) >= limit:
            break
    return out


def bronze_domain_tag_pass(master_key: str, *, limit: int = 12) -> dict:
    """Ask alfred-reasoner to suggest domain tags for untagged Bronze."""
    stats: dict = {
        "domain_tag_reviewed": 0,
        "domain_tag_applied": 0,
        "domain_tag_proposed_new": 0,
        "domain_tag_failed": 0,
        "domain_tag_results": [],
        "domain_tag_digest": "",
    }
    try:
        known = load_known_domains()
        known_ids = known_domain_ids(known)
    except Exception as exc:  # noqa: BLE001
        log(f"warn: domain registry load failed: {exc}")
        stats["domain_tag_digest"] = f"_Domain registry load failed: {exc}_"
        return stats

    items = get_bronze_for_domain_tagging(limit=limit)
    if not items:
        stats["domain_tag_digest"] = digest_domain_tag_section([])
        return stats

    for item in items:
        stats["domain_tag_reviewed"] += 1
        doc = item["document"]
        meta = dict(item["metadata"])
        current = str(meta.get("repo_tag") or meta.get("domain") or "unknown")
        try:
            raw = litellm_chat_safe(
                master_key,
                "alfred-reasoner",
                build_domain_tag_user_prompt(doc, known, current_tag=current),
                DOMAIN_TAG_SYSTEM_PROMPT,
            )
            # Force JSON object responses when LiteLLM supports it (same as rubric).
            suggestion = parse_domain_tag_response(raw, known_ids)
            staged = ""
            if suggestion.is_new:
                path = stage_domain_proposal(suggestion, bronze_id=item["id"])
                staged = str(path)
                stats["domain_tag_proposed_new"] += 1
            else:
                stats["domain_tag_applied"] += 1
                doc = ensure_domain_line(doc, suggestion.suggested_domain)

            new_meta = apply_suggestion_to_meta(
                meta, suggestion, staged_path=staged
            )
            # Queue applied tags for Stage 4 rubric when still scratch bronze
            if (
                not suggestion.is_new
                and suggestion.confidence >= 3
                and str(new_meta.get("review_status") or "") in {"", "none"}
            ):
                new_meta["review_status"] = "pending-review"

            update_bronze_meta(item["id"], doc, new_meta)
            log(
                f"domain-tag: {item['id']} → {suggestion.suggested_domain} "
                f"new={suggestion.is_new} conf={suggestion.confidence}"
            )
            stats["domain_tag_results"].append(
                {
                    "bronze_id": item["id"],
                    "suggested_domain": suggestion.suggested_domain,
                    "is_new": suggestion.is_new,
                    "confidence": suggestion.confidence,
                    "rationale": suggestion.rationale,
                    "staged": staged,
                    "alternates": list(suggestion.alternate_domains),
                }
            )
            if not suggestion.is_new:
                known_ids.add(suggestion.suggested_domain)
        except Exception as exc:  # noqa: BLE001
            stats["domain_tag_failed"] += 1
            log(f"warn: domain-tag failed for {item['id']}: {exc}")

    stats["domain_tag_digest"] = digest_domain_tag_section(stats["domain_tag_results"])
    return stats


def embed(text: str) -> list[float]:
    data = http_json("POST", f"{OLLAMA}/api/embeddings", {"model": EMBED_TAG, "prompt": text}, timeout=180)
    return data["embedding"]


def upsert_gold(doc_id: str, document: str, meta: dict) -> None:
    cid = collection_id(GOLD)
    flush_models()  # full slot-2 (reasoner + coder 9B + security + legacy)
    vec = embed(document)
    http_json(
        "POST",
        f"{CHROMA}/collections/{cid}/upsert",
        {"ids": [doc_id], "documents": [document], "metadatas": [meta], "embeddings": [vec]},
        timeout=300,
    )
    flush_models(EMBED_TAG)


def update_bronze_meta(doc_id: str, document: str, meta: dict) -> None:
    cid = collection_id(BRONZE)
    flush_models()  # full slot-2 (reasoner + coder 9B + security + legacy)
    vec = embed(document)
    http_json(
        "POST",
        f"{CHROMA}/collections/{cid}/upsert",
        {"ids": [doc_id], "documents": [document], "metadatas": [meta], "embeddings": [vec]},
        timeout=300,
    )
    flush_models(EMBED_TAG)


def delete_bronze(doc_id: str) -> None:
    cid = collection_id(BRONZE)
    try:
        http_json("POST", f"{CHROMA}/collections/{cid}/delete", {"ids": [doc_id]}, timeout=60)
    except Exception as exc:  # noqa: BLE001
        log(f"warn: delete bronze {doc_id}: {exc}")


def memory_stage4(master_key: str) -> dict:
    from alfred_sentinel_config import ENABLE_MEMORY_STAGE4
    if not ENABLE_MEMORY_STAGE4:
        return {
            'pending_review_swept': 0,
            'chunks_evaluated': 0,
            'chunks_pruned': 0,
            'silver_pinned': 0,
            'gold_ratified': 0,
            'gold_staged': 0,
            'promotion_blocks': [],
            'domain_tag_reviewed': 0,
            'domain_tag_applied': 0,
            'domain_tag_proposed_new': 0,
            'domain_tag_failed': 0,
            'domain_tag_digest': '_skipped — set SENTINEL_ENABLE_MEMORY=1_',
        }

    stats = {
        "pending_review_swept": 0,
        "chunks_evaluated": 0,
        "chunks_pruned": 0,
        "silver_pinned": 0,
        "gold_ratified": 0,
        "gold_staged": 0,
        "promotion_blocks": [],
        "gold_deduped": 0,
        "domain_tag_reviewed": 0,
        "domain_tag_applied": 0,
        "domain_tag_proposed_new": 0,
        "domain_tag_failed": 0,
        "domain_tag_digest": "",
    }
    # Use/context-driven tagging before rubric promotion so unknown Bronze
    # gets repo_tag (or a staged new-domain proposal) from alfred-reasoner.
    tag_stats = bronze_domain_tag_pass(master_key, limit=12)
    for k in (
        "domain_tag_reviewed",
        "domain_tag_applied",
        "domain_tag_proposed_new",
        "domain_tag_failed",
        "domain_tag_digest",
    ):
        stats[k] = tag_stats.get(k, stats[k])

    pending = get_pending_review()
    stats["pending_review_swept"] = len(pending)
    for item in pending:
        stats["chunks_evaluated"] += 1
        doc = item["document"]
        meta = dict(item["metadata"])
        try:
            raw = litellm_chat_safe(
                master_key,
                "alfred-reasoner",
                (
                    "Return ONLY a JSON object with integer fields "
                    "debugging_friction, cross_project_reusability, "
                    "verification_status, actionability_density (each 1-5), "
                    "plus string fields domain, slug, skill_card.\n\n"
                    f"Learning to score:\n\n{doc[:6000]}"
                ),
                RUBRIC_SYSTEM_PROMPT,
            )
            try:
                score = parse_rubric_response(raw)
            except Exception as parse_exc:  # noqa: BLE001
                raise RuntimeError(f"rubric parse: {parse_exc}; raw={raw[:500]!r}") from parse_exc
            route = route_score(score)
            # Do not stage near-duplicate Gold cards when skills/<slug|domain> exists.
            skip_gold_reason = (
                gold_skill_already_exists(score) if route == "gold_stage" else None
            )
            if skip_gold_reason:
                log(
                    f"memory: {item['id']} score={score.total} gold→silver "
                    f"(dedupe: {skip_gold_reason})"
                )
                route = "silver_pin"
                stats.setdefault("gold_deduped", 0)
                stats["gold_deduped"] = int(stats.get("gold_deduped") or 0) + 1
            log(f"memory: {item['id']} score={score.total} route={route} domain={score.domain}")
            if route == "purge":
                delete_bronze(item["id"])
                stats["chunks_pruned"] += 1
            elif route == "silver_pin":
                meta.update(
                    {
                        "collection_tier": "silver",
                        "is_pinned": True,
                        "promotion_score": score.total,
                        "review_status": "silver",
                        "last_accessed_at": utc_now_iso(),
                        "superseded_by": meta.get("superseded_by") or "",
                    }
                )
                if skip_gold_reason:
                    meta["gold_dedupe_reason"] = skip_gold_reason[:200]
                update_bronze_meta(item["id"], score.skill_card or doc, meta)
                stats["silver_pinned"] += 1
            else:
                day = datetime.now(timezone.utc).strftime("%Y%m%d")
                gold_id = f"session:{score.domain}_{score.slug}_{day}"
                gold_meta = {
                    "collection_tier": "gold",
                    "repo_tag": score.domain,
                    "created_at": utc_now_iso(),
                    "last_accessed_at": utc_now_iso(),
                    "is_pinned": True,
                    "promotion_score": score.total,
                    "superseded_by": "",
                    "review_status": "gold",
                }
                upsert_gold(gold_id, score.skill_card, gold_meta)
                staged = stage_gold_promotion(score)
                stats["gold_ratified"] += 1
                stats["gold_staged"] += 1
                stats["promotion_blocks"].append(digest_promotion_block(score, staged))
                # mark bronze done / superseded
                meta.update(
                    {
                        "review_status": "promoted",
                        "promotion_score": score.total,
                        "superseded_by": gold_id,
                        "last_accessed_at": utc_now_iso(),
                    }
                )
                update_bronze_meta(item["id"], doc, meta)
        except Exception as exc:  # noqa: BLE001
            log(f"warn: memory stage4 failed for {item['id']}: {exc}")
            # Soft-fail: leave pending for next night
    flush_models()  # full slot-2 (reasoner + coder 9B + security + legacy)
    return stats
