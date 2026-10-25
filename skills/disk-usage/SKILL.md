---
name: disk-usage
description: >-
  Host capacity and duplicate-folder hunts. Prefer a depth-limited du tool;
  never rewrite mount paths; never invent inventory; propose only — no deletes.
primary_domain: disk-usage
domains: [disk-usage]
routing_tags: ["#domain:disk-usage"]
preferred_model: alfred-coder
---

# Host disk / duplicate folder hunts
#domain: disk-usage

## Hard rules

1. Keep the **full** path the human or tools gave you. Never “simplify” `/mnt/DATA/media` → `/mnt/media`.
2. Prefer **one** depth-limited directory size listing, then answer. Do not spam recursive listings.
3. Structure the reply from evidence sections when available:
   - largest dirs (capacity)
   - name-similar folder groups (duplicate **shortlist**)
   - reclaim hints (samples, nested mirrors) when present
4. Never invent “no duplicates” if name-similar groups are non-empty.
5. Never start host deletes/hashes from chat alone — shortlist for human approval.
6. If the human asks for a mutator script, obey `#domain:safe-script-production`.

## Reply shape

1. One line: used% / total if known.
2. Top largest dirs from evidence.
3. Duplicate shortlist (quote paths).
4. Ask which groups (if any) to handle offline.

## Never

Rewrite mounts; invent inventory; claim a delete/hash job started; generic “here are some actions you might consider” without evidence.
