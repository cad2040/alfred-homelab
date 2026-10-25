# Learning path — build an Alfred-like lab

Ordered path from “chat UI on Ollama” to **rails** (aliases, skills, Bronze, eval, nightly HITL, memory prune). Each step is useful alone; later steps assume earlier ones.

## 0. Mindset

Read [architecture.md](architecture.md). Accept: small local models need **policy and measurement**. You are not installing ChatGPT.

## 1. Gateway + aliases (day 1)

1. Follow [../deploy/HUMAN.md](../deploy/HUMAN.md) (GPU or CPU compose).
2. Point clients at LiteLLM **aliases**, not raw Ollama tags.
3. Pull one instruct model; smoke `/v1/chat/completions`.

**Done when:** Continue/Open WebUI talks to `alfred-coder` on `127.0.0.1:4000`.

## 2. Fail-closed publishes (day 1–2)

1. Read skill [`docker-ufw`](../skills/docker-ufw/SKILL.md).
2. Keep Ollama/LiteLLM on localhost until DOCKER-USER is understood.

**Done when:** nothing inference-related is on `0.0.0.0` without a firewall story.

## 3. Gold skills + inject (week 1)

1. Read [guides/gold-skills.md](guides/gold-skills.md) and [guides/wire-middleware.md](guides/wire-middleware.md).
2. Example Compose already mounts `skills/` + `alfred_routing_skills.py`.
3. Chat with `#domain:docker-ufw` and confirm the skill text appears in behavior.

**Done when:** `#domain:` changes answers in a measurable way.

## 4. Bronze budgets (week 1–2)

1. Read [guides/bronze-budgets.md](guides/bronze-budgets.md).
2. Optionally pull a small **base** FIM tag for `/api/generate` summaries.
3. Keep `bronze_budgets.yaml` in sync when you change `num_ctx`.

**Done when:** long chats compress instead of returning empty streams.

## 5. VRAM honesty (week 2)

1. Read [`vram-runtime`](../skills/vram-runtime/SKILL.md).
2. Set `OLLAMA_MAX_LOADED_MODELS=2`; pin FIM; hot-swap one specialist.

**Done when:** autocomplete stops dying every time you load a 7B chat model.

## 6. Model challenge → wire → drop (week 2–3)

1. Read [guides/model-challenge-wire-drop.md](guides/model-challenge-wire-drop.md) — **pattern**; CLIs are private.
2. Practice with the keyword harness against two LiteLLM model entries, or wait until you write your own wire script.
3. Never rewire on a tied score or a smaller ctx without eyes open.

**Done when:** you can explain pull → A/B → wire-with-rollback → drop, even if you edit YAML by hand.

## 7. Eval harness (week 3+)

1. Read [guides/eval-harness.md](guides/eval-harness.md) — this repo’s harness is a **keyword toy**.
2. Run the minimal examples under [`examples/harness/`](../examples/harness/).
3. Grow your own challenges from real failures (that is the whole point).

**Done when:** at least one gate encodes a scar you care about (e.g. DOCKER-USER / CONFIRM).

## 8. Nightly Sentinel (week 4+)

1. Read [guides/nightly-sentinel.md](guides/nightly-sentinel.md).
2. Start from [`examples/sentinel/sentinel_skeleton.py`](../examples/sentinel/sentinel_skeleton.py).
3. HITL forever — digests are **signal**, not authority to mutate prod.

**Done when:** a cron job writes a morning digest you actually read.

## 9. Memory tiers & Chroma prune (week 4+)

1. Read [guides/memory-tiers-curation.md](guides/memory-tiers-curation.md) — **gates only** in this repo; the nightly prune job is private.
2. Score notes with [`examples/curation/RUBRIC_CHECKLIST.md`](../examples/curation/RUBRIC_CHECKLIST.md); run [`route_score.py`](../examples/curation/route_score.py).
3. In your private lab: Bronze capture → nightly purge/silver → **HITL only** for Gold git skills.
4. Success metric once prune exists: Bronze collection size **sawtooths** (grows by day, shrinks after nightly), not climbs forever.

**Done when:** you can explain purge vs silver vs gold_stage, and you refuse auto-Gold without a human merge.

## 10. What stays private

Your real `domains.yaml`, digests, DR, personal IoT, SMTP, master keys, and full middleware forks with estate paths — keep those in a **private** repo. Curate outward; don’t dump inward.
