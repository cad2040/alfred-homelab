---
name: vram-runtime
description: >-
  Single-GPU VRAM model: pin a small FIM/autocomplete in slot-1; hot-swap one
  chat specialist in slot-2 (OLLAMA_MAX_LOADED_MODELS=2). No unload theatre.
primary_domain: vram-runtime
domains: [vram-runtime]
routing_tags: ["#domain:vram-runtime"]
preferred_model: alfred-coder
---

# VRAM runtime (12GB-class boxes)
#domain: vram-runtime

## Hard rules

1. **FIM / autocomplete stays pinned** in slot-1 (`keep_alive: -1` or equivalent). Do not unload it to “make room” for the planner.
2. **One specialist** (coder / reasoner / planner / security) occupies **slot-2** and hot-swaps peers.
3. Set **`OLLAMA_MAX_LOADED_MODELS=2`** (pin + one specialist). Claiming “three 7Bs fit” is how autocomplete dies.
4. Clients should select the **alias** they need; do not invent flush hashtags that unload the pin.
5. Keep a flush list of specialist backend tags for orderly unload between roles.

## Never

Unload the FIM pin for a specialist; assume three large instruct models coexist; treat slot-2 eviction as “amnesia” without explaining hot-swap.
