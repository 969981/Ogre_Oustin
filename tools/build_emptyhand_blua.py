#!/usr/bin/env python3
"""Build a Lua 5.4 .blua for Ogre Oustin using official luac (no full decompile).

Usage:
  python tools/build_emptyhand_blua.py path/to/main.blua build/main.blua
  python tools/build_emptyhand_blua.py path/to/main.blua build/main.blua --luac luac5.4

The tool does not extract/pack Oodle archives or install a Switch mod.
Only use a user-owned, decompressed, matching Pokemon SV main.blua.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATCH = ROOT / "patches/lua/ogre_oustin_emptyhand.lua"
BYTECODE_MAGIC = b"\x1bLua\x54\x00\x19\x93\x0d\x0a\x1a\x0a"
EXPECTED_SIZES = bytes((4, 8, 8))
ANCHORS = (
    b"C6D182891100F211D",
    b"C9FD31BF01E130013",
    b"CBA116AC4A909C38C",
    b"F5F3E9041FE44C3C6",
    b"FD9E6D41945878085",
)


def validate_chunk(name: str, data: bytes) -> None:
    if len(data) < 33 or not data.startswith(BYTECODE_MAGIC):
        raise ValueError(
            f"{name}: not standard Lua 5.4 bytecode; decompress/extract .blua first"
        )
    if data[12:15] != EXPECTED_SIZES:
        raise ValueError(
            f"{name}: unexpected instruction/integer/number sizes: "
            f"{tuple(data[12:15])}, expected (4, 8, 8)"
        )


def locate_luac(explicit: str | None) -> str:
    if explicit:
        return explicit
    for name in ("luac5.4", "luac54", "luac"):
        p = shutil.which(name)
        if p:
            return p
    raise RuntimeError("Lua 5.4 compiler not found; install lua5.4 or use --luac")


def run(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(
            "command failed: " + " ".join(args)
            + "\n" + (result.stderr or result.stdout).strip()
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path, help="uncompressed binary Lua 5.4 main.blua")
    ap.add_argument("output", type=Path, help="new .blua (never overwrite input)")
    ap.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    ap.add_argument("--luac", help="path to luac5.4, e.g. /usr/bin/luac5.4")
    ns = ap.parse_args()

    try:
        source = ns.input.resolve(strict=True)
        patch = ns.patch.resolve(strict=True)
        out = ns.output.resolve()
        if source == out or patch == out:
            raise ValueError("refusing to overwrite source or patch")
        raw = source.read_bytes()
        validate_chunk("input", raw)
        missing = [s.decode("ascii") for s in ANCHORS if s not in raw]
        if missing:
            raise ValueError(
                "4.0.0 script anchors missing; refusing to build: "
                + ", ".join(missing)
            )
        patch_data = patch.read_bytes()
        if not patch_data.startswith(b"-- OGRE_OUSTIN_PATCH_BEGIN"):
            raise ValueError("unexpected patch identity; use the dedicated empty-hand hook")
        if b"__OGRE_OUSTIN_EMPTYHAND_V1" not in patch_data:
            raise ValueError("empty-hand patch marker missing")
        luac = locate_luac(ns.luac)
        out.parent.mkdir(parents=True, exist_ok=True)
        run([luac, "-p", str(source)])
        run([luac, "-p", str(patch)])
        # Original binary executes FIRST. Hook code runs SECOND.
        # Official Lua 5.4 luac combines binary and source chunks.
        with tempfile.TemporaryDirectory(prefix="ogre-blua-", dir=out.parent) as td:
            temp = Path(td) / "combined.blua"
            run([luac, "-o", str(temp), str(source), str(patch)])
            run([luac, "-p", str(temp)])
            combined = temp.read_bytes()
            validate_chunk("output", combined)
            if combined == raw:
                raise ValueError("output unchanged; hook was not bundled")
            temp.replace(out)
        print("build: Lua 5.4 compile/merge/PARSE OK")
        print("original SHA256:", hashlib.sha256(raw).hexdigest())
        print("patched  SHA256:", hashlib.sha256(out.read_bytes()).hexdigest())
        print("output:", out)
        print("NEXT: package with Trinity at script/lua/bin/release/main/main.blua")
        print("NOT YET VERIFIED: Violet 4.0.0 actual runtime loading and interaction")
        return 0
    except (OSError, ValueError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
