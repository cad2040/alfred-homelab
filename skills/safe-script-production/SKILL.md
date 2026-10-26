---
name: safe-script-production
description: >-
  Lane A: careful repo micro-edits. Lane B: dry-run default host rm/mv; mutate
  only with CONFIRM=yes. Prefer for DECISION: apply / alfred-coder.
source_repo: cad2040/alfred-homelab
source_path: skills/safe-script-production
primary_domain: safe-script-production
domains: [safe-script-production]
routing_tags: ["#domain:safe-script-production"]
preferred_model: alfred-coder
---

# Safe script production
#domain: safe-script-production

## Pick one lane

**Lane A — workspace edit** (`DECISION: apply`, named repo files):
read+edit on real paths. Prefer **one file per turn**. No `sed -i` as the edit path.

**Lane B — host destructive** (rm/mv/rsync): dry-run default; mutate only with
`CONFIRM=yes` in the environment. Print the plan first.

## Rules
1. `set -euo pipefail` on bash; never ignore failures silently.
2. Prefer archive/move over `rm -rf` on important data.
3. No secrets in scripts or skill text.
4. After chmod/write: verify the path exists and is executable if claimed.

## Template (Lane B)

```bash
#!/usr/bin/env bash
set -euo pipefail
DRY_RUN=1
[[ "${CONFIRM:-}" == "yes" ]] && DRY_RUN=0
plan() { echo "WOULD: $*"; }
run() { if [[ "$DRY_RUN" -eq 1 ]]; then plan "$@"; else "$@"; fi; }
# run rm -rf /path/to/target
```

## Never
Blind `rm -rf`; mutate without CONFIRM on Lane B; paste secrets; invent paths.
