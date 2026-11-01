#!/usr/bin/env python3
"""Package independent Atmosphere and Ryujinx cheat TXT ZIPs for SV 4.0.0.

Scarlet is an UNVERIFIED CANDIDATE: the Violet RVA and original opcode are
assumptions for Scarlet, NOT established from its original ELF/NSO.
Both versions are unconditional shared damage-record writes, not boss-only OHKO.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

PATCH_NAME = "SV400_Always65535Damage_Cheat"
RVA = 0x01536214
ORIGINAL_WORD = 0x79413BF9       # LDRH W25, [SP, #0x9C] (verified only in Violet)
PATCHED_WORD = 0x529FFFF9        # MOVZ W25, #0xFFFF
GAMES = {
    "Scarlet": {
        "tid": "0100A3D008C5C000",
        "bid": "421C5411B487EB4D049DD065FEC9547773E8E598",
        "status": ("UNVERIFIED CANDIDATE. Scarlet's original main+0x1536214 "
                   "and control flow have NOT been verified; even matching "
                   "LDRH opcode at this RVA cannot establish correctness."),
    },
    "Violet": {
        "tid": "01008F6008C5E000",
        "bid": "709BFD66115298640155FCC4979DBA151C7CC79A",
        "status": ("Violet original opcode at main+0x1536214 statically verified; "
                   "cheat-loading and gameplay effects NOT verified."),
    },
}


def cheat_text() -> str:
    """Atmosphere cheat VM: original-word guard, write, end."""
    return (
        "[SV 4.0.0 Damage Record 65535 EXPERIMENTAL]\n"
        f"14050000 {RVA:08X} {ORIGINAL_WORD:08X}\n"
        f"04000000 {RVA:08X} {PATCHED_WORD:08X}\n"
        "20000000\n"
    )


def package(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = cheat_text().encode("utf-8")
    assets: list[Path] = []
    for game, info in GAMES.items():
        tid, bid, short = info["tid"], info["bid"], info["bid"][:16]
        suffix = "_CANDIDATE" if game == "Scarlet" else ""
        for target in ("Atmosphere", "Ryujinx"):
            if target == "Atmosphere":
                inner = f"atmosphere/contents/{tid}/cheats/{short}.txt"
                instruction = "Extract at the Switch SD-card root."
            else:
                inner = f"mods/contents/{tid}/{PATCH_NAME}/cheats/{short}.txt"
                instruction = (
                    "Extract in the Ryujinx/Ryubing portable data directory that contains mods/. "
                    "In a non-portable install, open the game's Mods Directory, "
                    f"and copy {PATCH_NAME}/cheats/{short}.txt into that game directory. "
                    "Enable the code in Manage Cheats."
                )
            name = f"Pokemon_{game}_4.0.0_{target}_65535_CHEAT{suffix}.zip"
            notes = (
                f"Pokemon {game} 4.0.0 / Title ID {tid}\n"
                f"Build ID (20 bytes): {bid}\n"
                f"Cheat TXT BID prefix (8 bytes): {short}\n"
                f"{info['status']}\n\n"
                "This is NOT a guaranteed 65535 damage, raid-only or boss-only modification. "
                "It writes to an intermediate damage-result instruction, which can be limited "
                "or overwritten later. Other attacks may be affected.\n"
                "Back up your save; test offline only. Do NOT use in public multiplayer.\n"
                "DO NOT enable the previous IPS at the same RVA together with this cheat.\n"
                "The first line of code compares the target's original instruction; "
                "a mismatch makes this code skip the write. This DOES NOT prove Scarlet validity.\n"
                "Disabling a code does not undo a patch already written into executable memory: "
                "fully close and relaunch the game after removing/disabling it.\n"
                "IMPORTANT: On Atmosphere, if a cheats/<BID>.txt file already exists, "
                "BACK IT UP and MERGE THE NEW CODE BLOCK instead of overwriting it.\n\n"
                f"Install: {instruction}\n"
                f"Installed path: {inner}\n"
                f"Cheat VM: compare MAIN+0x{RVA:08X} == 0x{ORIGINAL_WORD:08X}, "
                f"write 0x{PATCHED_WORD:08X}.\n"
            )
            outfile = output_dir / name
            with zipfile.ZipFile(outfile, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr(inner, payload)
                z.writestr("README.txt", notes)
            assets.append(outfile)
            print(f"BUILT {outfile} -> {inner}")
        # Provide standalone BID.txt files for manual merge, no content rewriting.
        raw_dir = output_dir / "cheats" / game
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{short}.txt").write_bytes(payload)
    return assets


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = p.parse_args()
    for path in package(args.output_dir):
        print(path, path.stat().st_size)


if __name__ == "__main__":
    main()
