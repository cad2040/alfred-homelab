# Alfred architecture — strengths & weaknesses

Comparison baseline: typical homelab AI boxes — Open WebUI or LibreChat + Ollama on a 3060/4060, maybe one Compose file, rarely eval harnesses or estate-specific skills.

Alfred is **not** competing with cloud agents. It is a **personal estate OS with local LLMs as a subsystem**. Grade it that way.

Hands-on path: [LEARNING_PATH.md](LEARNING_PATH.md). Middleware wire-up: [guides/wire-middleware.md](guides/wire-middleware.md).

## Verdict in one line

Among single-builder homelabs, Alfred-style stacks sit in the **top few percent for ops discipline and institutional memory**, and only **average for raw model IQ / UX polish**. The rails are the product; the 7B/9B weights are the engine.

**Strong specialized system, fragile if you treat it like ChatGPT.**

---

## Strengths (ahead of most labs)

### 1. Estate-shaped Gold skills + routing
Most labs dump a system prompt and pray. Alfred uses **domain IDs**, phrase triggers, applicability scoring, inject caps, and optional `#domain:` force-routes. Closer to an internal developer platform than “I installed Open WebUI.”

### 2. Fail-closed host ops
Preflight mounts / UUIDs, VRAM flock, MemAvailable thresholds, DOCKER-USER awareness, refuse dangerous on-metal paths — **homelab adulting**. Many AI boxes happily OOM and republish MySQL to `0.0.0.0`.

### 3. Measured trust, not vibes
An eval harness with written trust bands is rare. Weekly Flash-style judges are useful **if** you keep HITL and never auto-promote from a score alone.

### 4. Honest VRAM model
FIM (small autocomplete) **pinned** in slot-1; one specialist **hot-swapped** in slot-2 on 12GB is how 3060 boxes actually work. Pretending three 7Bs “fit” kills Twinny/FIM.

### 5. HITL as constitution
Digests, Spec Kit drafts, staged model wires — **signal not authority**. The community often roleplays “autonomous agents” until a bad `rm` or firewall rule.

### 5b. Memory tiers with prune
Bronze capture is cheap; Silver auto-promote is gated; Gold is **human-only**. Nightly rubric + purge keeps Chroma from filling with vibes — see [guides/memory-tiers-curation.md](guides/memory-tiers-curation.md).

### 6. Plan vs implement split
Separate **planner** and **coder** aliases (even soft 9B planners) beat “paste megaprompt into Agent.” Few labs separate those roles at all.

### 7. Bronze rolling context
When messages (+ tools) approach specialist `num_ctx`, compress the middle (threshold ≈ 0.61 × ctx) instead of silent empty streams. Budgets should track the wired window — see [guides/bronze-budgets.md](guides/bronze-budgets.md).

### 8. Challenge → wire → drop
Pull a candidate, A/B against an alias with harness + judge, wire with smoke/auto-rollback, or drop weights cleanly. Prefer baseline when pass rates **tie**; smaller `num_ctx` is a capability loss short packs miss.

---

## Parity with good labs (not unique)

- Ollama + LiteLLM + Open WebUI / Continue
- Optional local websearch inject
- Security specialist model (narrow but smart)
- Email digests / cron ops
- 8k–32k chat contexts — adequate, not frontier

---

## Weaknesses (be honest with adopters)

### Effectiveness limiters

1. **Small weights.** 7B/9B will not match frontier cloud models for hard reasoning or large refactors. You win on **estate recall**, lose on **general intelligence**. Budget truth: better GPU later or accept cloud for hard problems.

2. **Operator tax.** Right alias, `#domain:`, review drafts. Untagged chat is mediocre. Either embrace the tax or invest in Auto-Selector UX so the tax is invisible.

3. **Cold-load / hot-swap friction.** Slot-2 eviction feels like “Alfred forgot” unless clients and docs set expectations.

4. **Routing / skill inject brittleness.** Wrong domain or invented skill names waste a turn. Eval packs catch some of this; users still need discipline.

### Ops debt

5. **Private SoT drift.** Public extracts lag live labs. Document that explicitly.
6. **Judge ≠ truth.** Gemini/Flash scores follow harness gates; infra flakes (`Connection refused`) look like model failure.
7. **Security surface.** Master keys, published ports, tool servers — Compose examples must default to localhost binds.

---

## Recommended alias map (example)

| Alias | Role | Notes |
|-------|------|-------|
| `alfred-fim` | Autocomplete / FIM | Small base model, pinned, ~8k |
| `alfred-coder` | Coding + tools | Instruct chat, OpenAI-compat `/v1` |
| `alfred-reasoner` | General reason | May need `think:false` on thinking models |
| `alfred-technical-planner` | Spec / plan only | Never implement |
| `alfred-security` | Exposure / hardening review | Often smaller ctx for VRAM |

Tune `num_ctx` per alias and keep Bronze thresholds in sync.

---

## Design principles (steal these)

1. **Aliases, not raw tags**, in clients — rewire backends without teaching every tool a new name.
2. **Skills are law for a domain**; system prompts are soft.
3. **Fail closed** on mounts, publishes, and destructive scripts.
4. **Measure before promote** — challenge packs, then wire, then drop if wrong.
5. **HITL for anything that mutates** hosts, firewalls, or production config.
