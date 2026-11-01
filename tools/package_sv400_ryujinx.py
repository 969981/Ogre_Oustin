#!/usr/bin/env python3
"""Repackage the verified single-instruction IPS for Ryujinx portable mods."""
from pathlib import Path
import hashlib
import zipfile
import argparse

BUILD_ID = "709bfd66115298640155fcc4979dba151c7cc79a"
TITLE_ID = "01008F6008C5E000"
PATCH_NAME = "SV400_Always65535Damage"
EXPECTED_IPS = bytes.fromhex("4950533332015363140004f9ff9f5245454f46")
RYUJINX_PATH = f"mods/contents/{TITLE_ID}/{PATCH_NAME}/exefs/{BUILD_ID}.ips"
OUTPUT_NAME = "Pokemon_Violet_4.0.0_Ryujinx_65535_IPS.zip"
README = """Ryujinx portable mode - Pokemon Violet 4.0.0

1. Close the game and Ryujinx.
2. Extract this ZIP into the emulator's publish/portable folder, merging mods/.
3. Check that mods/contents/01008F6008C5E000/SV400_Always65535Damage/exefs/
   contains the 709bfd66115298640155fcc4979dba151c7cc79a.ips file.
4. Temporarily remove the old duplicate from sdcard/atmosphere/exefs_patches.
5. In Ryujinx right-click Pokemon Violet -> Manage Mods -> enable the mod.
6. Fully restart the game and inspect the latest portable/Logs log for
   "Matching IPS patch" and the correct Build ID.

This uses the SAME instruction and SAME IPS as the Atmosphere variant.
No guaranteed one-hit KO: post-processing may clamp damage.
UNCONDITIONAL: applies wherever the instruction runs. Offline testing only.
"""

def build(output_dir: Path) -> Path:
    source = output_dir / "atmosphere" / "exefs_patches" / PATCH_NAME / f"{BUILD_ID}.ips"
    data = source.read_bytes()
    if data != EXPECTED_IPS:
        raise ValueError("IPS differs from the validated single-instruction patch")
    result = output_dir / OUTPUT_NAME
    with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(RYUJINX_PATH, data)
        zf.writestr("README_Ryujinx.txt", README)
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    out = build(args.output_dir)
    print(f"Ryujinx ZIP: {out} ({out.stat().st_size} bytes)")
    print(f"IPS SHA256: {hashlib.sha256(EXPECTED_IPS).hexdigest()}")

if __name__ == "__main__":
    main()
