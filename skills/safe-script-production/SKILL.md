---
name: safe-script-production
description: >-
  Gates for LLM-authored shell/Python that mutates hosts or repos: verbatim
  paths from evidence, dry-run first, set -euo pipefail, no no-op mv/ln loops,
  no inventing paths. Transferable coding.
primary_domain: safe-script-production
domains: [safe-script-production, coding]
routing_tags:
  - "#domain:safe-script-production"
  - "#domain:coding"
preferred_model: alfred-coder
applicability:
  buckets: [coding]
  apply_when:
    - "bash script"
    - "shell script"
    - "write a script"
    - "dry-run"
    - "set -euo"
    - "rm -rf"
    - "rsync"
    - "destructive"
  exclude_when: []
  min_hits: 2
---

# Safe script production (host / repo mutations)
#domain: safe-script-production

## Hard rules

1. **Paths verbatim from evidence** (tool output, user paste, directory listings). Never invent or “pretty” a path.
2. **Dry-run by default.** Print the plan or use `rsync -n` / `diff`. Mutation only behind `CONFIRM=yes` (or equivalent).
3. **`set -euo pipefail`** (bash) or fail-fast equivalent; quote every expansion (`"$path"`).
4. **Preflight every source:** `[[ -e "$src" ]]` before `mv`/`rm`/`ln`. On miss → error + non-zero exit.
5. **No no-op / loop links.** Forbidden: `mv "$x" "$(dirname "$x")"` when already there; circular `ln -s`.
6. **Parent/child folders are not duplicates.** Do not “merge” a child into its parent as consolidation.
7. **Peer folders only** for KEEP/DROP style reclaim: one KEEP + one DROP; `rm -rf --one-file-system` after confirm — not `mv DROP into KEEP`.
8. One mutation block per script unless the human asks for a batch with an explicit list.
9. Labeled plan above the fence: what changes, risk, dry-run default.
10. No raw tool-call JSON / fake task footers in the answer.

## Template

```bash
#!/usr/bin/env bash
set -euo pipefail
CONFIRM="${CONFIRM:-no}"
KEEP="/path/from/evidence/A"
DROP="/path/from/evidence/B"
[[ -e "$KEEP" && -e "$DROP" ]] || { echo "preflight failed"; exit 1; }
echo "KEEP=$KEEP"
echo "DROP=$DROP"
if [[ "$CONFIRM" != "yes" ]]; then
  echo "dry-run only — re-run with CONFIRM=yes to delete DROP"
  exit 0
fi
rm -rf --one-file-system -- "$DROP"
```

## Never

Invent paths; mutate without CONFIRM; nest DROP under KEEP; disable errexit “to keep going.”
