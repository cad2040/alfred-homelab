---
name: coach-this-prompt
description: >
  Core co-pilot skill: rewrites rough thoughts into agent-optimized messages on
  "Coach this Prompt:" / #domain:prompt-coach. Binds a real #domain: id, routes
  a model hint, does not execute the coached task unless asked.
source_repo: cad2040/alfred-homelab
source_path: skills/coach-this-prompt
primary_domain: prompt-coach
domains: [prompt-coach]
routing_tags: ["#domain:prompt-coach"]
preferred_model: alfred-reasoner
trigger_phrase: "Coach this Prompt:"
---

# Coach this Prompt
#domain: prompt-coach

## Hard rules (do not soften)

1. Activate on `Coach this Prompt:` / `#domain:prompt-coach` / explicit coach ask.
2. **Do not execute** the coached task unless the user explicitly says to run it next.
3. Always use the output format below.
4. **Domain binding:** prefer an explicit `#domain:<id>` from the template registry
   (`docker-ufw`, `safe-script-production`, `vram-runtime`, `bronze-context`,
   `skill-gold-authoring`, `prompt-coach`). Never invent ids. If none fit, use
   `#domain:coding` or `#domain:software-planning` as umbrellas and state
   `domain_confidence: high|medium|low` under Assumptions.
5. **Model hint** in Suggested next step: implement → `alfred-coder`; plan/spec →
   `alfred-technical-planner`; coach/reason → `alfred-reasoner`.
6. LAN-private only — no SaaS LLM APIs; never suggest `keep_alive: -1`.
7. Preserve real intent; rewrite dangerous asks to safer scoped steps.
8. **Maturity bar** inside `## Coached prompt`: Issue · Context · Evidence ·
   Desired outcome · Confirm · Acceptance checks · Do not touch.

## Output format (always)

```markdown
## Coached prompt
#domain:<specific-id-or-umbrella>
## Issue
…
## Context
…
## Evidence
…
## Desired outcome
…
## Confirm the issue is real
…
## Remediation constraints
- Do not touch: …
## Acceptance checks
…
## Agent routing
- model: alfred-coder | alfred-reasoner | alfred-technical-planner

## What changed
- …

## Assumptions
- domain_confidence: high|medium|low — <why>
- …

## Suggested next step
- `Send coached prompt to <model>` or `Revise: …` — do not auto-run
```

## Never
Execute the coached task unbidden; invent domain ids; suggest permanent FIM pins.
