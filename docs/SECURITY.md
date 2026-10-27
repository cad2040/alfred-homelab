# Security for an Alfred-like homelab

**Audience:** operators running local LLMs with tools, file writes, or host scripts on a personal machine (typically a 12GB GPU box).

This is not a compliance handbook. It is the scar tissue from giving a small model enough rope to hang the host.

## Principles

1. **Rails first, weights second.** Policy, binds, and HITL matter more than which 7B you pulled this week.
2. **Fail closed.** If mounts, keys, or publishes are wrong, refuse — do not “helpfully” continue.
3. **Gold is law; chat is not.** Injectable skills that mutate hosts require a human gate. Never auto-promote model drafts into production skills.
4. **Localhost by default.** Template Compose in this repo publishes LiteLLM/Ollama on `127.0.0.1`, not the LAN.

## The threat model

A local LLM with tools is not a chatbot. It is a **privileged co-operator** that can:

| Capability | What goes wrong |
|------------|-----------------|
| Shell / script generation | Plausible `rm`, firewall, or `chmod` that destroys mounts or opens the box |
| File write / Apply | Overwrites configs, `.env`, or skill cards with confident nonsense |
| Path hallucination | Rewrites `/mnt/data/media` → `/mnt/media`, “fixes” UUIDs, invents KEEP/DROP peers |
| Tool loops | Repeated host probes, VRAM thrash, or accidental publish of services |
| Prompt injection via retrieved text | Bronze notes, web snippets, or pasted logs that say “ignore previous rules” |

You are defending against **mistakes and over-trust**, not primarily against
nation-state attackers on a home LAN. The usual failure mode is accepting a
tidy-looking Apply that still mutates the wrong host path or firewall rule.

Assume:

- The model will occasionally **omit dry-run**, invent paths, or skip `CONFIRM=yes`.
- Gold skill inject can still be **wrong-routed**; wrong domain ≈ wrong permissions narrative.
- Anything bound to `0.0.0.0` on a home LAN is reachable by guests, IoT, and the next compromised laptop.

## Sandboxing & Human-In-The-Loop (HITL)

### Why HITL is mandatory for mutators

Gold cards such as `safe-script-production` and `docker-ufw` encode **how** to change the host. They do not get to **apply** those changes without you.

| Allowed without HITL | Requires HITL |
|----------------------|---------------|
| Read-only diagnosis, digests, drafts | Firewall rules, UFW/DOCKER-USER edits |
| Staging a Gold draft under review | Merging into `skills/<slug>/` + ingest |
| Keyword eval / challenge packs | Running generated bash/Python that mutates disks |
| Bronze capture / Silver pin (gated) | Auto-promoting Silver → Gold |

**Rule:** if the output can change disk, network, or boot behavior, the human is the control plane. The model proposes; you Apply.

### Practical sandboxing (homelab-scale)

Do these before you chase exotic agent frameworks:

1. **Dry-run first.** Scripts print the plan; mutation needs an explicit `CONFIRM=yes` (or equivalent).
2. **One fence, verbatim paths.** No invented KEEP/DROP trees; paths must come from evidence (`du_depth`, listings you trust).
3. **Read-only mounts for teaching trees.** Example Compose mounts skills/config `:ro` into LiteLLM.
4. **No blind Agent write** on live `/etc`, compose, or `.env`. Prefer draft → review → apply.
5. **Separate planner vs implementer aliases.** Planning models should not own destructive tools.
6. **VRAM flock / single specialist.** Stops “helpful” parallel jobs from thrashing the only GPU while a mutator is mid-flight.

Sandboxing here means **narrow tools + review**, not a Kubernetes sidecar mesh.

## Fail-closed defaults

### Localhost binds

Example Compose publishes:

- LiteLLM → `127.0.0.1:4000`
- Ollama → `127.0.0.1:11434`

Inside the container the process may listen on `0.0.0.0` (Docker networking). **Host publish** is what matters: keep the left-hand side of `ports:` on loopback unless you have a deliberate LAN story (VPN, firewall, auth).

Avoid:

```yaml
ports:
  - "4000:4000"      # LAN-wide LiteLLM
  - "11434:11434"    # LAN-wide Ollama
```

Prefer:

```yaml
ports:
  - "127.0.0.1:4000:4000"
  - "127.0.0.1:11434:11434"
```

### Master key required

LiteLLM’s master key is not decoration. Generate a long random value in `.env` (`LITELLM_MASTER_KEY`). Clients must send `Authorization: Bearer …`. Empty or `sk-1234` teaching leftovers belong in demos that never leave the box.

If the key leaks on a localhost-only bind, risk is mostly other local users/processes. If you republish to the LAN without a key (or with a toy key), you handed neighbors a GPU API.

### Refuse dangerous defaults

Fail closed means the stack should **stop** when:

- Required mounts / UUIDs are missing
- MemAvailable / VRAM budgets are blown
- A script lacks dry-run or confirmation
- A Gold promotion would auto-ingest without human Apply

“Make it work” by binding MySQL, Ollama, or LiteLLM to `0.0.0.0` is the opposite of this design.

## What this public repo does *not* claim

- Not a hardened multi-tenant product
- Not an SSO / audit / SIEM story
- Not safe to expose on the public internet
- Teaching Sentinel / harness / curation are **skeletons and patterns** — your private cron, mail, and prune jobs need the same HITL discipline

## Checklist before tools leave the sandbox

```
[ ] LiteLLM + Ollama published on 127.0.0.1 only
[ ] LITELLM_MASTER_KEY is long, random, only in .env (not git)
[ ] Mutating Gold skills reviewed; no auto-ingest from digests
[ ] Generated scripts: dry-run + CONFIRM; paths from evidence
[ ] No 0.0.0.0 host publishes “just for the phone on Wi-Fi”
[ ] You accept operator tax: wrong #domain: → pause, don’t force Apply
```

## Related reading

- [architecture.md](architecture.md) — rails-first tradeoffs + request-flow diagram
- [guides/gold-skills.md](guides/gold-skills.md) — skills as domain law
- [guides/memory-tiers-curation.md](guides/memory-tiers-curation.md) — Bronze/Silver/Gold HITL
- [guides/nightly-sentinel.md](guides/nightly-sentinel.md) — digest as signal, not authority
- Skill cards: `safe-script-production`, `docker-ufw`
