# Deploy scripts

| Script | Job |
|--------|-----|
| [`bootstrap.sh`](bootstrap.sh) | `.env` if missing → `compose up` → wait → pull bases + create Modelfiles |
| [`smoke.sh`](smoke.sh) | Wait for LiteLLM → `/v1/models` + `#domain:docker-ufw` + Coach checks |
| [`sync-skills.sh`](sync-skills.sh) | Restart LiteLLM after skill/domain edits |
| [`teardown.sh`](teardown.sh) | `compose down` (`--volumes` drops Ollama data) |

```bash
./scripts/bootstrap.sh
# set LITELLM_MASTER_KEY in deploy/compose/.env
./scripts/smoke.sh
# edit skills/ or routing/domains.yaml
./scripts/sync-skills.sh
```

- **GPU:** default Compose.  
- **CPU:** `ALFRED_CPU=1 ./scripts/bootstrap.sh` (slow; bring-up only).  
- **Smoke deps:** `curl` required; `python3` / `jq` optional.

Private labs often add vector-DB ingest + a git-mirror sync helper. This
template treats **this repo** as SoT — no host data-mirror paths.
