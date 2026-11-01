#!/usr/bin/env python3
"""SV400 Raid boss 1x HP + no shield; Trinity mod ZIP builder.

Uses the *user's* pristine Scarlet 4.0.0 main.blua only. Violet output is
a labeled unverified compatibility candidate, not a validated Violet patch.
No original game data is committed to the repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from build_raid_profile_experiment import Audit, compile_patch, ORIGINAL_SIZE, SOURCE_SHA, FIELDS, OFFSET_SJ

TITLE_IDS = {"scarlet": "0100A3D008C5C000", "violet": "01008F6008C5E000"}
MAIN_PATH = "script/lua/bin/release/main/main.blua"

def inspect_patch(binary: bytes) -> dict:
    """Check patched Lua 5.4 structure and intended literal writes."""
    reader = Audit(binary)
    reader.get(31)
    reader.u8()
    reader.node()
    if reader.i != len(binary) or len(reader.matches) != 1:
        raise ValueError("modified Lua must parse to EOF with exactly one CE6.Get")
    proto = reader.matches[0]
    if proto["code_count"] != 547 or len(proto["consts"]) != 80:
        raise ValueError("unexpected modified CE6.Get layout")
    codes = proto["codes"]
    wanted = {153: 1, 157: 0, 161: 0}
    for index, (site, value) in enumerate(wanted.items()):
        stub = 538 + 3 * index
        if (codes[site] >> 7) - OFFSET_SJ + site + 1 != stub:
            raise ValueError("invalid entry JMP")
        if codes[stub + 1] != FIELDS[site][2]:
            raise ValueError("displaced original SETFIELD mismatch")
        if (codes[stub + 2] >> 7) - OFFSET_SJ + stub + 3 != site + 1:
            raise ValueError("invalid return JMP")
        if (codes[stub] >> 15) - 65535 != value:
            raise ValueError("modified literal mismatch")
    return {"target": "CE6.Get / root/7833", "changed_pcs": list(wanted),
            "literals": {"hpCoef": 100, "powerChargeTrigerHp": 0,
                         "powerChargeTrigerTime": 0}}

def package(original: Path, out: Path, game: str, violet_candidate: bool = False) -> dict:
    if game not in TITLE_IDS:
        raise ValueError("not a supported game")
    if game == "violet" and not violet_candidate:
        raise ValueError("Violet game-resource fingerprint not confirmed; pass --violet-candidate")
    raw = original.read_bytes()
    if len(raw) != ORIGINAL_SIZE or hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError("original Scarlet 4.0.0 main.blua SHA/size guard failed")
    patch, _ = compile_patch(raw, {"hp_coef": 1, "no_shield": True,
                                   "shield_rates": [None, None, None]})
    audit = inspect_patch(patch)
    out.mkdir(parents=True, exist_ok=True)
    state = "VIOLET_CANDIDATE" if game == "violet" else "SCARLET_VERIFIED_SOURCE"
    stem = f"Pokemon_{game.title()}_4.0.0_Raid_1xHP_NoShield_TRINITY_{state}"
    filename = stem + ".zip"
    is_candidate = game == "violet"
    caveat = ("Scarlet-derived Lua asset; Violet compatibility unverified"
              if is_candidate else "Scarlet 4.0.0 source fingerprint verified")
    info = (
        'display_name = "Raid 1x HP + No Shield (EXPERIMENT)"\n'
        'author_name = "969981"\n'
        'version = "0.1.0-experimental"\n'
        f'description = "{caveat}; offline tests only"\n'
    )
    with zipfile.ZipFile(out / filename, "w", zipfile.ZIP_DEFLATED, compresslevel=7) as z:
        z.writestr("info.toml", info)
        z.writestr(MAIN_PATH, patch)
    report = {
        "game": game, "title_id": TITLE_IDS[game], "version": "4.0.0",
        "source_asset_version": "Scarlet 4.0.0",
        "violet_compatibility": "UNVERIFIED" if is_candidate else "N/A",
        "modified_lua_sha256": hashlib.sha256(patch).hexdigest(),
        "trinity_zip_sha256": hashlib.sha256((out / filename).read_bytes()).hexdigest(),
        "audit": audit, "zip": filename,
        "status": "STATIC_LUA_VERIFIED__GAME_AND_REWARD_UNTESTED",
        "distribution": "Trinity input ZIP, NOT direct Atmosphere IPS",
    }
    (out / (stem + ".json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--out", default=Path("dist"), type=Path)
    parser.add_argument("--game", required=True, choices=list(TITLE_IDS))
    parser.add_argument("--violet-candidate", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(package(args.original, args.out, args.game,
                                 args.violet_candidate), ensure_ascii=False, indent=2))
    except (ValueError, AssertionError, OSError) as exc:
        parser.exit(2, f"Refused: {exc}\n")

if __name__ == "__main__":
    main()
