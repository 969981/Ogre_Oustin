#!/usr/bin/env python3
"""Append the Ogre Oustin experimental monkey patch to a user-extracted SV main Lua.

This repository intentionally does not redistribute the game's main script.
The tool only patches a file supplied by the user.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

BEGIN = "-- OGRE_OUSTIN_PATCH_BEGIN"
END = "-- OGRE_OUSTIN_PATCH_END"

ANCHORS = (
    "C6D182891100F211D",
    "FCE25070892D46E56",
    "F466EB120F65C4DF8",
    "F5F3E9041FE44C3C6",
    "CE506B90C88D90C92",
    "C9FD31BF01E130013",
    "CC07CA97E7F9D78F4",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="user-extracted base main Lua")
    parser.add_argument("output", type=Path, help="patched output Lua")
    parser.add_argument(
        "--patch",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "patches" / "lua" / "ogre_oustin_patch.lua",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="append even when one or more 3.0.1-era anchors are absent",
    )
    args = parser.parse_args()

    base = args.input.read_bytes()
    try:
        text = base.decode("utf-8")
    except UnicodeDecodeError as exc:
        print(f"error: input is not UTF-8 Lua text: {exc}", file=sys.stderr)
        return 2

    patch = args.patch.read_text(encoding="utf-8")

    if BEGIN in text or END in text:
        print("error: Ogre Oustin patch marker already exists in input", file=sys.stderr)
        return 3

    missing = [anchor for anchor in ANCHORS if anchor not in text]
    if missing and not args.force:
        print("error: script does not match expected hash anchors:", file=sys.stderr)
        for anchor in missing:
            print(f"  - {anchor}", file=sys.stderr)
        print("Refusing to patch. Verify the 4.0.0 script or pass --force only after manual review.", file=sys.stderr)
        return 4

    if BEGIN not in patch or END not in patch:
        print("error: patch file is missing begin/end markers", file=sys.stderr)
        return 5

    out_text = text.rstrip() + "\n\n" + patch.rstrip() + "\n"
    out = out_text.encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(out)

    print(f"input : {args.input}")
    print(f"sha256: {sha256(base)}")
    print(f"output: {args.output}")
    print(f"sha256: {sha256(out)}")
    if missing:
        print("warning: forced patch with missing anchors: " + ", ".join(missing))
    else:
        print("anchor check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
