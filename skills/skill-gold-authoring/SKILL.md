---
name: skill-gold-authoring
description: >-
  Author Tier-1 Gold skills: SKILL.md inject ≤4500 chars; optional reference;
  wire routing/domains.yaml; no placeholders. Soft-park deferred work under skills/_soft/.
source_repo: cad2040/alfred-homelab
source_path: skills/skill-gold-authoring
primary_domain: skill-gold-authoring
domains: [skill-gold-authoring]
routing_tags: ["#domain:skill-gold-authoring"]
preferred_model: alfred-reasoner
---

# Skill Gold authoring
#domain: skill-gold-authoring

## Caps
| Path | Cap | Counted |
|------|-----|---------|
| LiteLLM inject | **4500** | `SKILL.md` only |
| Optional Chroma ingest | **5500** | SKILL + reference (private upgrade) |

## Hard rules
1. Lead with `#domain:` + rules + **Verified template** inside `SKILL.md`.
2. No `TODO` / `TBD` / placeholder text; no secrets.
3. Same change: update `routing/domains.yaml` (+ restart LiteLLM / `scripts/sync-skills.sh`).
4. Densify an existing skill before inventing a near-duplicate slug.
5. **Soft / deferred** future projects: `skills/_soft/<slug>/` (not ingested). Promote = move to `skills/<slug>/`, densify with real notes, wire domains. Private labs may add rubric ≥15 gates.

## Checklist
```
[ ] len(SKILL.md) ≤ 4500 — template complete
[ ] domains.yaml updated
[ ] No secrets
[ ] Soft-park if the project is not active yet
```

## Never
Ship placeholders; duplicate near-identical skills; put deferred work in live Gold.
