# Gold skills (for humans & agents)

A **Gold skill** is a short, enforceable domain card: hard rules, a template, and explicit “never” lines. Routing injects the right card(s) into the model context; the model is not asked to invent policy every turn.

## Card shape

```yaml
---
name: example-domain
description: >-
  One or two lines: when to use this skill.
primary_domain: example-domain
domains: [example-domain]
routing_tags: ["#domain:example-domain"]
preferred_model: alfred-coder   # or your alias
---

# Title
#domain: example-domain

## Hard rules
1. …

## Template
…

## Never
…
```

## Authoring rules

1. **Imperative “never” beats vibes.** If a failure mode burned you once, write it as a rule.
2. **One primary domain** per card; optional umbrella domains (`coding`, `software-planning`) for transferable skills.
3. **Applicability cues** (keywords) help routers merge ≤1 transferable skill without dumping the whole library.
4. **No secrets** in skill text — paths, patterns, and commands only.
5. Promote only after reuse; raw learnings stay private until scored.

See example cards under [`../../skills/`](../../skills/) and `skills/skill-gold-authoring/`.

## For agents deploying Alfred-like stacks

- Do not invent `#domain:` IDs that are not in the registry.
- Prefer injecting **SKILL.md** (short) over whole reference books.
- Cap inject size; leave headroom for the user turn and tools.
