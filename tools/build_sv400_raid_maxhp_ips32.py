#!/usr/bin/env python3
"""Rebuild experimental Violet 4.0.0 IPS32 (attacker entity ID == 1 ONLY).

Not Raid-only; ordinary battles and zero damage may be affected. Test offline only.
No Nintendo executable content is bundled.
"""
import argparse
import hashlib
from pathlib import Path
import struct

TITLE_ID = "01008F6008C5E000"
BUILD_ID = "709BFD66115298640155FCC4979DBA151C7CC79A"
EXPECTED_ELF_SHA256 = "d17403eaa9d844db82f647fd2f1518806b10c0518d53602fc0ac1766298fdba0"
TEXT_FILE_BASE = 0x8D8  # ELF .text file offset, not NSO IPS offset
NSO_IPS_BASE = 0x100
STORE_RVA = 0x1536218
CAVE_RVA = 0x420BE4
ORIG_STORE = struct.pack("<I", 0x78004F99)

# clang -target aarch64-linux-gnu verified instructions; W8 remains unmodified.
INSTRUCTIONS = [
    0x7940B30A,  # ldrh w10,[x24,#0x58] : target maxHP
    0xF9404BE9,  # ldr x9,[sp,#0x90] : attacker pointer
    0xB9405129,  # ldr w9,[x9,#0x50] : attacker ID candidate
    0x7100053F,  # cmp w9,#1
    0x1A990159,  # csel w25,w10,w25,eq : change candidate only for ID1
    0x78004F99,  # strh w25,[x28,#4]! : displaced original store
]


def branch(origin: int, destination: int) -> bytes:
    delta = destination - origin
    if delta % 4 or not -(1 << 27) <= delta < (1 << 27):
        raise ValueError("AArch64 unconditional branch out of range")
    return struct.pack("<I", 0x14000000 | ((delta >> 2) & 0x3FFFFFF))


def record(offset: int, payload: bytes) -> bytes:
    if not 0 <= offset <= 0xFFFFFFFF or not 1 <= len(payload) <= 0xFFFF:
        raise ValueError("IPS32 record invalid")
    return offset.to_bytes(4, "big") + len(payload).to_bytes(2, "big") + payload


def build(elf: bytes) -> bytes:
    actual = hashlib.sha256(elf).hexdigest()
    if actual != EXPECTED_ELF_SHA256:
        raise ValueError("ELF SHA-256 mismatch: " + actual)
    if elf[TEXT_FILE_BASE + STORE_RVA:TEXT_FILE_BASE + STORE_RVA + 4] != ORIG_STORE:
        raise ValueError("Original damage STRH mismatch")
    if elf[TEXT_FILE_BASE + CAVE_RVA:TEXT_FILE_BASE + CAVE_RVA + 28] != bytes(28):
        raise ValueError("Expected unused text padding is not zero")
    trampoline = b"".join(struct.pack("<I", op) for op in INSTRUCTIONS)
    trampoline += branch(CAVE_RVA + 24, STORE_RVA + 4)
    assert len(trampoline) == 28
    return (
        b"IPS32"
        + record(CAVE_RVA + NSO_IPS_BASE, trampoline)
        + record(STORE_RVA + NSO_IPS_BASE, branch(STORE_RVA, CAVE_RVA))
        + b"EEOF"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--elf", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    patch = build(args.elf.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(patch)
    print(f"IPS32: {len(patch)} bytes; sha256={hashlib.sha256(patch).hexdigest()}")
    print("WARNING: NOT RAID-ONLY. Attacker ID1 can occur in other battles.")


if __name__ == "__main__":
    main()
