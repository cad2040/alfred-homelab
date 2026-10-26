---
name: vram-runtime
description: >-
  GPU locks for local LLM labs: flock before batch jobs; keep_alive 5m interactive /
  flush 0; single resident MAX_LOADED=1 + KV q8_0; FIM on-demand only (not pinned).
source_repo: cad2040/alfred-homelab
source_path: skills/vram-runtime
primary_domain: vram-runtime
domains: [vram-runtime]
routing_tags: ["#domain:vram-runtime"]
preferred_model: alfred-coder
---

# VRAM / Ollama runtime
#domain: vram-runtime

## Rules
1. Before long batch LLM jobs: `flock -w 600 /var/lock/alfred-vram.lock` (or your lab lock path).
2. Interactive specialists: `keep_alive` **5m**; flush with **`keep_alive: 0`**. Do **not** pin FIM with `keep_alive: -1`.
3. **One resident** at a time (`OLLAMA_MAX_LOADED_MODELS=1`) — swap coder / reasoner / planner by selecting the alias.
4. FIM (`qwen2.5-coder:1.5b-base`) is autocomplete / Bronze **fallback only**.
5. Optional gates: `MemAvailable` (not raw `free -m`); free VRAM before loading a heavy tag.
6. Prefer `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0` on 12GB-class GPUs.
7. Ollama listen `127.0.0.1` — clients go through LiteLLM.

## Template

```bash
exec 9>/var/lock/alfred-vram.lock
flock -w 600 9 || { echo "VRAM lock timeout"; exit 1; }
curl -s http://127.0.0.1:11434/api/generate \
  -d '{"model":"qwen2.5-coder:7b-instruct","keep_alive":0}' >/dev/null
```

```bash
# Compose / systemd env (honest 12GB posture)
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KV_CACHE_TYPE=q8_0
```

## Never
Permanent FIM pin; two chat specialists resident; `MAX_LOADED_MODELS>1` on 12GB without measuring; LLM batch jobs without a shared flock.
