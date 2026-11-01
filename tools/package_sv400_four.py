#!/usr/bin/env python3
"""Package Violet's known IPS and an explicitly UNVERIFIED Scarlet candidate."""
from __future__ import annotations
import argparse
from pathlib import Path
import struct
import zipfile

PATCH_NAME = "SV400_Always65535Damage"
IPS32_OFFSET = 0x1536214 + 0x100
PATCH_BYTES = bytes.fromhex("f9ff9f52")
VIOLET_IPS = bytes.fromhex("4950533332015363140004f9ff9f5245454f46")
GAMES = {
    "Scarlet": {
        "tid": "0100A3D008C5C000",
        "bid": "421C5411B487EB4D049DD065FEC9547773E8E598",
        "status": "UNVERIFIED CANDIDATE: Scarlet RVA/instruction bytes not checked against an original Scarlet 4.0.0 main. The Violet RVA is assumed, NOT established.",
    },
    "Violet": {
        "tid": "01008F6008C5E000",
        "bid": "709BFD66115298640155FCC4979DBA151C7CC79A",
        "status": "Violet 4.0.0 RVA/original instruction statically checked; gameplay effect NOT verified.",
    },
}

def candidate_ips32() -> bytes:
    return b"IPS32" + struct.pack(">IH", IPS32_OFFSET, 4) + PATCH_BYTES + b"EEOF"

def make_zip(path: Path, install_path: str, data: bytes, readme: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(install_path, data)
        zf.writestr("README.txt", readme)

def build(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    violet_source = output_dir / "atmosphere" / "exefs_patches" / PATCH_NAME / (GAMES["Violet"]["bid"] + ".ips")
    if violet_source.read_bytes() != VIOLET_IPS:
        raise ValueError("Violet base IPS does not match the existing known bytes")
    if candidate_ips32() != VIOLET_IPS:
        raise ValueError("Candidate IPS32 format changed")
    output = []
    for game, info in GAMES.items():
        tid, bid = info["tid"], info["bid"]
        data = candidate_ips32() if game == "Scarlet" else violet_source.read_bytes()
        atmosphere_path = "atmosphere/exefs_patches/" + PATCH_NAME + "/" + bid + ".ips"
        ryujinx_path = "mods/contents/" + tid + "/" + PATCH_NAME + "/exefs/" + bid + ".ips"
        common = (
            f"Pokemon {game} 4.0.0 / Title ID {tid} / main NSO Build ID {bid}\n\n"
            + info["status"] + "\n\n"
            + "Patch: one unconditional AArch64 instruction, assuming main+0x1536214:\n"
            + "LDRH W25,[SP,#0x9C] -> MOV W25,#0xFFFF.\n"
            + "NOT RAID-ONLY and NOT GUARANTEED TO INFLICT 65535 DAMAGE or ONE-HIT KO.\n"
            + "Other logic can clamp/overwrite damage. Back up saves and test offline only.\n"
            + "Never use in online or public multiplayer.\n"
            + "Delete the patch folder and restart game to uninstall.\n"
        )
        marker = "_CANDIDATE" if game == "Scarlet" else ""
        atm_zip = output_dir / f"Pokemon_{game}_4.0.0_Atmosphere_65535{marker}.zip"
        ry_zip = output_dir / f"Pokemon_{game}_4.0.0_Ryujinx_65535{marker}.zip"
        make_zip(atm_zip, atmosphere_path, data,
                 common + "\nAtmosphere: extract to the Switch SD card root and fully restart the game.\n")
        make_zip(ry_zip, ryujinx_path, data,
                 common + "\nRyujinx / Ryubing portable: extract into the emulator's portable data directory "
                 "(the folder containing mods/), enable the mod and fully restart the game.\n"
                 "For regular installs, use the emulator's user-data mods directory instead.\n"
                 "Do not load the Atmosphere and Ryujinx copy simultaneously.\n")
        output.extend((atm_zip, ry_zip))
        print(game + ": " + atm_zip.name + " | " + ry_zip.name)
    return output

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    for asset in build(args.output_dir):
        print(asset, asset.stat().st_size, "bytes")

if __name__ == "__main__":
    main()
