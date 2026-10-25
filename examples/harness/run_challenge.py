#!/usr/bin/env python3
"""Minimal challenge runner against a LiteLLM OpenAI-compatible endpoint."""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--model", default="alfred-coder")
    ap.add_argument("--base", default=os.environ.get("LITELLM_BASE", "http://127.0.0.1:4000"))
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument(
        "--system",
        default="You are Alfred. Obey any #domain skill rules. Be precise.",
    )
    args = ap.parse_args()
    key = os.environ.get("LITELLM_MASTER_KEY", "").strip()
    if not key:
        raise SystemExit("LITELLM_MASTER_KEY required")

    prompt = args.prompt_file.read_text(encoding="utf-8")
    body = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": args.max_tokens,
        "tools": [],
        "tool_choice": "none",
    }
    req = urllib.request.Request(
        f"{args.base.rstrip('/')}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw = json.loads(resp.read().decode())
    except Exception as exc:  # noqa: BLE001
        (args.out_dir / "error.txt").write_text(str(exc), encoding="utf-8")
        raise SystemExit(f"request failed: {exc}") from exc

    msg = ((raw.get("choices") or [{}])[0].get("message") or {})
    text = msg.get("content") or ""
    (args.out_dir / "raw.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "response.md").write_text(text, encoding="utf-8")
    (args.out_dir / "meta.json").write_text(
        json.dumps({"model": args.model, "prompt": str(args.prompt_file)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(text[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
