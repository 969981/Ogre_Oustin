#!/usr/bin/env python3
"""Build a single-instruction IPS32 patch for Pokemon Violet 4.0.0."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import struct
import zipfile

BUILD_ID = "709bfd66115298640155fcc4979dba151c7cc79a"
EXPECTED_ELF_SHA256 = "d17403eaa9d844db82f647fd2f1518806b10c0518d53602fc0ac1766298fdba0"
PATCH_NAME = "SV400_Always65535Damage"
PATCH_RVA = 0x1536214
NSO_HEADER_SIZE = 0x100
ELF_TEXT_OFFSET = 0x8D8
ORIGINAL_INSTRUCTION = bytes.fromhex("f93b4179")  # LDRH W25,[SP,#0x9c]
PATCH_INSTRUCTION = bytes.fromhex("f9ff9f52")     # MOV W25,#0xffff
INSTALL_PATH = f"atmosphere/exefs_patches/{PATCH_NAME}/{BUILD_ID}.ips"
WARNING = """Pokemon Violet v4.0.0 - single-instruction 65535 damage patch

Install: copy the atmosphere folder to the root of your SD card, then restart the game.
Uninstall: delete atmosphere/exefs_patches/SV400_Always65535Damage.

Replaces exactly one AArch64 instruction at main+0x1536214:
  original: LDRH W25,[SP,#0x9C]
  patched:  MOV W25,#0xFFFF

This is UNCONDITIONAL. It is not raid-only, player-only, or boss-only. The game
may clamp/overwrite damage later, so guaranteed one-hit KO is NOT established.
Only for Pokemon Violet 4.0.0 with Build ID 709bfd66115298640155fcc4979dba151c7cc79a.
Not for Scarlet or other game versions. Use in isolated/offline testing;
back up your save before testing. Do not use in online/public multiplayer.
"""

def make_ips32() -> bytes:
    # Atmosphere IPS addresses are decompressed NSO offsets, including the 0x100 header.
    offset = PATCH_RVA + NSO_HEADER_SIZE
    return b"IPS32" + struct.pack(">IH", offset, len(PATCH_INSTRUCTION)) + PATCH_INSTRUCTION + b"EEOF"

def verify_elf(elf: Path) -> None:
    with elf.open("rb") as fp:
        digest = hashlib.file_digest(fp, "sha256").hexdigest()
        if digest != EXPECTED_ELF_SHA256:
            raise ValueError(f"ELF SHA256 mismatch: {digest}")
        fp.seek(ELF_TEXT_OFFSET + PATCH_RVA)
        found = fp.read(4)
    if found != ORIGINAL_INSTRUCTION:
        raise ValueError(f"unexpected instruction at ELF text+RVA: {found.hex()}")

def build(output_dir: Path, elf: Path | None = None) -> tuple[Path, Path]:
    if elf is not None:
        verify_elf(elf)
    output_dir.mkdir(parents=True, exist_ok=True)
    ips_path = output_dir / INSTALL_PATH
    ips_path.parent.mkdir(parents=True, exist_ok=True)
    ips_path.write_bytes(make_ips32())
    zip_path = output_dir / "Pokemon_Violet_4.0.0_Always65535Damage_IPS.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(ips_path, INSTALL_PATH)
        zf.writestr("README.txt", WARNING)
    return ips_path, zip_path

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--elf", type=Path, help="optional local ELF for fail-closed verification")
    args = parser.parse_args()
    ips, package = build(args.output_dir, args.elf)
    print(f"IPS32: {ips} ({ips.stat().st_size} bytes)")
    print(f"ZIP:   {package} ({package.stat().st_size} bytes)")
    print(f"IPS_SHA256: {hashlib.sha256(ips.read_bytes()).hexdigest()}")

if __name__ == "__main__":
    main()
