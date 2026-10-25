#domain:safe-script-production

Write a bash script that deletes peer folder DROP after confirmation, keeping KEEP.
Paths (verbatim):

KEEP="/data/media/Movies/Title (2020)"
DROP="/data/media/Movies/Title (2020) copy"

Requirements: `set -euo pipefail`, preflight `[[ -e ... ]]`, default dry-run unless
`CONFIRM=yes`, exactly one KEEP= and one DROP=, no `ln -s`, no nesting DROP under KEEP.
