#!/usr/bin/env python3
"""Minimal nightly Sentinel skeleton (optional depth — not day-1 template).

Writes a morning digest via LiteLLM. Does NOT git push, does NOT apply config
changes, does NOT invent VRAM unload theatre (respect MAX_LOADED=1 + flock).

Env:
  LITELLM_BASE          default http://127.0.0.1:4000/v1
  LITELLM_MASTER_KEY    required
  DIGEST_DIR            default ./digests/morning
  SENTINEL_MODEL        default alfred-reasoner
  SENTINEL_LOCK         default /tmp/alfred-sentinel.lock
"""
from __future__ import annotations

import fcntl
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def log(msg: str) -> None:
    print(msg, flush=True)


def chat(model: str, system: str, user: str, *, base: str, key: str) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    req = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode())
    return (
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    )


def main() -> int:
    base = os.environ.get("LITELLM_BASE", "http://127.0.0.1:4000/v1")
    key = os.environ.get("LITELLM_MASTER_KEY", "").strip()
    if not key:
        raise SystemExit("LITELLM_MASTER_KEY required")
    digest_dir = Path(os.environ.get("DIGEST_DIR", "./digests/morning"))
    model = os.environ.get("SENTINEL_MODEL", "alfred-reasoner")
    lock_path = Path(os.environ.get("SENTINEL_LOCK", "/tmp/alfred-sentinel.lock"))

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fh = lock_path.open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("another Sentinel holds the lock — exit")
        return 0

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    digest_dir.mkdir(parents=True, exist_ok=True)
    out = digest_dir / f"{day}.md"

    # Replace with real telemetry in your private lab.
    telemetry_blob = (
        f"date_utc: {day}\n"
        "note: skeleton telemetry only — wire docker/ollama/disk collectors privately.\n"
        "rule: respect MAX_LOADED=1 + flock; never git push from Sentinel.\n"
    )

    system = (
        "You are Alfred Sentinel. Produce a short morning ops digest in markdown. "
        "Use checklists. Propose actions; never claim you already mutated production."
    )
    user = f"Telemetry:\n```\n{telemetry_blob}\n```\nWrite today's digest."
    log(f"calling {model} …")
    body = chat(model, system, user, base=base, key=key)

    text = f"# Alfred morning digest ({day} UTC)\n\n{body.strip()}\n"
    out.write_text(text, encoding="utf-8")
    log(f"wrote {out}")
    log("HITL: read the digest before applying any suggestion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
