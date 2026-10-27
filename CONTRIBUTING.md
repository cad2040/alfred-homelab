# Contributing

Thanks for caring about local-LLM lab rails.

## What belongs here

- Sanitized deploy patterns, middleware twins, scripts, and **ops-core** Gold skills
- Fixes to bootstrap/smoke/docs clarity
- New skills that are **generic** (no private hostnames, family IoT, or secrets)

## What does not belong here

- Private estate dumps (full personal `domains.yaml`, digests, DR secrets)
- Real API keys, master keys, SMTP credentials
- Personal IoT stacks or host mount paths without scrubbing
- Enabling websearch proxies or judge paths that assume a private network

## Skill PRs

1. Follow `skills/skill-gold-authoring/SKILL.md`.
2. Include hard rules + template + never-list; keep inject ≤4500 chars.
3. Wire `routing/domains.yaml` in the same change.
4. Prefer improving an existing card over near-duplicates.
5. Soft-park deferred projects under `skills/_soft/` — do not ship as live Gold.

## Scrub checklist (before any PR)

- [ ] No real LAN CIDRs, hostnames, or `/mnt/...` paths from a private lab  
- [ ] No master keys, SMTP creds, or `.env` contents  
- [ ] No personal IoT / family device skills or domain ids  
- [ ] Docs say “reference / template,” not “my live box”  

## Tone

Honest about weaknesses (local weights, operator tax). No “replaces ChatGPT”
claims. This is a **co-pilot template**, not an autonomous agent kit.
