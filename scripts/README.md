# Deploy scripts

| Script | Job |
|--------|-----|
| [`bootstrap.sh`](bootstrap.sh) | `.env` if missing → `compose up` → pull coder (+ optional FIM) |
| [`smoke.sh`](smoke.sh) | `/v1/models` + `#domain:docker-ufw` + `Coach this Prompt:` checks |
| [`sync-skills.sh`](sync-skills.sh) | Restart LiteLLM after skill/domain edits |
| [`teardown.sh`](teardown.sh) | `compose down` (`--volumes` drops Ollama data) |

```bash
./scripts/bootstrap.sh
./scripts/smoke.sh
# edit skills/ or routing/domains.yaml
./scripts/sync-skills.sh
```

CPU-only: `ALFRED_CPU=1 ./scripts/bootstrap.sh`

Private estates often add Chroma ingest + git-mirror sync (`alfred-sync-skills`).
This template treats **this repo** as SoT — no `/mnt/alfred` mirror.
