# Learning path — after smoke

**Start with** [../README.md](../README.md) → `./scripts/bootstrap.sh` →
`./scripts/smoke.sh`. Come here only when you want optional depth.

Ordered upgrades from “gateway works” toward a fuller Alfred-like lab. Each step
is useful alone; later steps assume earlier ones.

## 0. Mindset

Read [architecture.md](architecture.md) and [PRIVATE_VS_TEMPLATE.md](PRIVATE_VS_TEMPLATE.md).
Accept: small local models need **policy and measurement**. You are not installing ChatGPT.

## 1. Gateway + aliases (day 1) — done if smoke passed

Prefer LiteLLM aliases in Continue/Open WebUI. Keep publishes on localhost.

## 2. Fail-closed publishes

Read [`docker-ufw`](../skills/docker-ufw/SKILL.md). Replace `YOUR_LAN_CIDR` before applying iptables.

## 3. Gold skills + Coach

Read [guides/gold-skills.md](guides/gold-skills.md) and [guides/wire-middleware.md](guides/wire-middleware.md).
Use `Coach this Prompt:` before heavy Agent turns.

## 4. Bronze budgets

[guides/bronze-budgets.md](guides/bronze-budgets.md). Optional: `ALFRED_PULL_FIM=1 ./scripts/bootstrap.sh`.

## 5. VRAM honesty

[`vram-runtime`](../skills/vram-runtime/SKILL.md) — MAX_LOADED=1, no permanent FIM pin.
Alias map (14B coder / 9B reasoner+planner / Foundation-Sec): [architecture.md](architecture.md).

## 6. Challenge → wire → drop (pattern only)

[guides/model-challenge-wire-drop.md](guides/model-challenge-wire-drop.md) — CLIs stay private.

## 7. Eval harness (toy)

[guides/eval-harness.md](guides/eval-harness.md) + `examples/harness/`.

## 8. Nightly Sentinel (skeleton)

[guides/nightly-sentinel.md](guides/nightly-sentinel.md) + `examples/sentinel/`.

## 9. Memory tiers / prune (gates)

[guides/memory-tiers-curation.md](guides/memory-tiers-curation.md) + `examples/curation/`.

## Done when

You can explain what is **template** vs **private upgrade**, and you have not
pretended this repo is a full estate OS.
