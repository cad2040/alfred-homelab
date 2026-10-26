#!/usr/bin/env python3
"""Simple keyword gate for optional-depth harness packs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--response", type=Path, required=True)
    ap.add_argument("--need", required=True, help="comma-separated substrings (case-insensitive)")
    ap.add_argument("--forbid", default="", help="comma-separated forbidden substrings")
    args = ap.parse_args()
    text = args.response.read_text(encoding="utf-8", errors="replace").lower()
    need = [s.strip().lower() for s in args.need.split(",") if s.strip()]
    forbid = [s.strip().lower() for s in args.forbid.split(",") if s.strip()]
    missing = [s for s in need if s not in text]
    hit_forbid = [s for s in forbid if s in text]
    ok = not missing and not hit_forbid
    result = {
        "ok": ok,
        "missing": missing,
        "forbid_hits": hit_forbid,
    }
    print(json.dumps(result))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
