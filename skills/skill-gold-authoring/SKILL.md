---
name: skill-gold-authoring
description: >-
  Author short Gold skills: hard rules + template in SKILL.md, dual size caps
  for inject vs ingest, no placeholders or secrets, transferable applicability.
primary_domain: skill-gold-authoring
domains: [skill-gold-authoring]
routing_tags: ["#domain:skill-gold-authoring"]
preferred_model: alfred-coder
---

# Skill Gold authoring
#domain: skill-gold-authoring

## Dual size caps (example — tune for your stack)

| Path | Cap (chars) | Counted |
|------|-------------|---------|
| Router **inject** | **4500** | `SKILL.md` only |
| Vector **ingest** | **5500** | `SKILL.md` + optional `reference.md` |

Exceeding either often **silently truncates**. Put the verified template in `SKILL.md`, not only in a long reference file the inject path never sees.

## Hard rules

1. Lead with `#domain:` + imperative rules + a **copy-paste template** inside `SKILL.md`.
2. No `TODO` / `TBD` / placeholder paths; no secrets or `.env` values.
3. Register the domain in your router config in the same change as the skill.
4. Promote from raw notes only after human confirm + real reuse — not vibes.
5. Densify an existing skill before inventing a near-duplicate slug.
6. **Transferable** skills: also tag an umbrella domain (`coding` / `software-planning`) and declare `applicability` cues (`apply_when`, `min_hits≥2`).

## Checklist

```
[ ] len(SKILL.md) ≤ inject cap — template complete
[ ] len(SKILL+ref) ≤ ingest cap — measured before embed
[ ] Router registry updated
[ ] No secrets
[ ] Transferable? umbrella domain + applicability block
```
