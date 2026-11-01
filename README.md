# Ogre_Oustin

Pokémon Scarlet / Violet **Ogre Oustin'（打鬼祭）** reverse-engineering notes and experimental Lua-patch design.

Current target: **Pokémon Violet 4.0.0**. Static ELF work in this repository was performed against the uploaded `Violet4.0.0.elf` whose GNU Build ID is `709bfd66115298640155fcc4979dba151c7cc79a`.

## Current conclusion

The high-level Ogre Oustin' game rules are implemented in the game's large Lua/Haxe-generated script layer rather than as three simple native functions in `main`.

The useful high-level call chain is now understood well enough to prototype the following without directly writing the fruit matrix:

- **Smart Balloon** — after a legitimate balloon event, grant only the still-needed fruit by reusing the original local `OnReceiveGetKinomi` path.
- **Auto Deposit** — reuse the original `TryOblation` path so Carry decrement, 507 Oblation traffic, Storage update, 513 synchronization, UI, scoring and clear checks stay on the normal path.
- **Instant Round** — repeatedly perform the two operations above; do **not** force a clear flag. The original `F58184E938BDF8E80` clear check is allowed to become true naturally.

The experimental patch is in [`patches/lua/ogre_oustin_patch.lua`](patches/lua/ogre_oustin_patch.lua). Use [`tools/patch_main_lua.py`](tools/patch_main_lua.py) to append it to a user-extracted base script. No Nintendo/Game Freak game script or asset is included in this repository.

## V2 research — full Carry at the start of every Level (2026-10-24)

A separate **Stage Start Full Carry** design has been documented; it is **not yet an implemented or runtime-validated mod**.

- When each new Level enters Gameplay, automatically prepare the four colors in the player's **held/Carry** inventory up to that Level's actual requirement; **do not** fill Storage, automatically deliver, or force CLEAR.
- Unlike the existing Smart Balloon / Instant Round modes, the player still manually delivers fruit to the original baskets. These modes should be mutually exclusive.
- The screenshot example has requirements **14 + 4 + 12 + 11 = 41**, exceeding the game's ordinary 30-fruit Carry capacity, so capacity consistency is a mandatory part of the design.
- The script-side preferred hook is `C6D182891100F211D::FCAFA8ED8BFD0E068`, **after** its original Gameplay/Reset sequence returns; hash-name semantics come from a 3.0.1-era public script and still require comparison with the extracted 4.0.0 main Lua.
- Default scope is **offline-only, read-only instrumentation first**. No multiplayer/production support is claimed.

See [technical design](docs/09-stage-start-full-carry-research.md) and [implementation/test plan](docs/10-stage-start-full-carry-implementation-tests.md).

## Recommended follow-up: Direct Empty-Hand Oblation (2026-10-24)

The **more direct V3 research option** is to approach a normal berry table with zero carried fruit and perform the **original A-button delivery interaction**. The public 3.0.1-era script shows a field interaction (`C4D2B0FE0245F3E65`) reaching `Scene::F5F3E9041FE44C3C6` (`TryOblation`), where the `held > 0` predicate blocks empty-hand delivery. The low-level Carry decrement already does nothing at zero, whereas the standard delivery callback increments Storage and runs the normal clear check.

This potentially avoids both collecting balloons and expanding the ordinary 30-fruit carry capacity. **4.0.0 runtime validation remains outstanding**, and the intended experiment is **offline-only, no write enabled by default**. See [11 — Direct Empty-Hand Oblation research](docs/11-direct-emptyhand-oblation-research.md). The prior [09 Full Carry design](docs/09-stage-start-full-carry-research.md) remains an alternative, not the preferred implementation.

## Empty-Hand Direct Oblation — experimental source PoC (2026-10-24)

A separate **open-source Lua Hook proof of concept** is now available at [patches/lua/ogre_oustin_emptyhand.lua](patches/lua/ogre_oustin_emptyhand.lua), with [Lua mock tests](tests/test_emptyhand.lua), a [Python/liblua runner](tests/run_emptyhand_tests.py), and [implementation/packaging guide](docs/12-emptyhand-implementation-options-and-poc.md). It temporarily relaxes the same-color held > 0 check only during the original local station delivery call; it does **not** automatically collect fruit, fill Storage directly, or force CLEAR.

**Status:** the local Lua simulation passes. Runtime deployment on Violet 4.0.0 is **not verified**, because the main .blua resource representation and correct compilation/repacking path still need validation. Do not copy the Lua source straight into the SD card or treat it as a working IPS/LayeredFS release. Default OFF/read-only; incompatible with the V1 Smart Balloon/Auto Deposit patch. Offline manual testing only.
## Library main.blua real-file verification (2026-10-24)

The user's Library `main.blua` was inspected directly: **12,912,264 bytes**, standard Lua 5.4 binary with **30,829 direct / 37,743 total** function prototypes. `liblua5.4` loads it successfully in binary mode without executing game code. All Ogre Oustin class/method hash anchors appear in parsed constants.

**Important variant finding:** its SHA-256 exactly matches the separately documented **Scarlet 4.0.0** bytecode (`c1a4f4e2625912cf0b739a642a79ba3357df0557a544b92da22a6cb139de2815`); it is **not yet proven to be the Violet 4.0.0 resource**. The builder now fails closed for this known Scarlet sample unless `--allow-known-scarlet` is explicitly supplied. No actual 12.9 MB multi-chunk luac merge or Switch runtime validation has yet been completed.

See [14 — real-file bytecode validation](docs/14-library-main-blua-validation-20261024.md) and [the build helper](tools/build_emptyhand_blua.py). The game bytecode itself is not distributed here.

## Documentation

- [`docs/14-library-main-blua-validation-20261024.md`](docs/14-library-main-blua-validation-20261024.md) — actual Library file fingerprint, parsed prototypes/anchors, Scarlet-vs-Violet caveat and binary Lua load verification.

- [`docs/13-v400-blua-bytecode-merge-trinity.md`](docs/13-v400-blua-bytecode-merge-trinity.md) — independently researched 4.0.0 Lua 5.4 bytecode format and no-decompile building with official luac; Trinity loose-file packaging.
- [`tools/build_emptyhand_blua.py`](tools/build_emptyhand_blua.py) — verified-header Lua 5.4 compiler orchestration (requires user-extracted original).

- [`docs/01-elf-4.0.0.md`](docs/01-elf-4.0.0.md) — 4.0.0 ELF layout and native Ojama findings.
- [`docs/02-lua-state-and-functions.md`](docs/02-lua-state-and-functions.md) — class map, 3×4 fruit state and important functions.
- [`docs/03-network-protocol.md`](docs/03-network-protocol.md) — packet IDs 506/507/511/513 and authority flow.
- [`docs/04-lua-patch-design.md`](docs/04-lua-patch-design.md) — exact monkey-patch points and Smart Balloon / Auto Deposit / Instant Round design.
- [`docs/05-layeredfs-trinity.md`](docs/05-layeredfs-trinity.md) — Trinity and Atmosphère/LayeredFS packaging workflow.
- [`docs/06-runtime-validation.md`](docs/06-runtime-validation.md) — validation matrix for 4.0.0, especially multiplayer.
- [`docs/07-sources.md`](docs/07-sources.md) — public source references used during analysis.
- [`docs/08-trpfd-4.0.0-main-lua.md`](docs/08-trpfd-4.0.0-main-lua.md) — independently confirmed 4.0.0 TRPFD Lua pack names and remaining extraction requirement.
- [`docs/09-stage-start-full-carry-research.md`](docs/09-stage-start-full-carry-research.md) — V2 new-Level auto-fill research, capacity >30 and exact candidate Lua hook.
- [`docs/10-stage-start-full-carry-implementation-tests.md`](docs/10-stage-start-full-carry-implementation-tests.md) — step-by-step development, read-only logging, testing and acceptance.
- [`docs/11-direct-emptyhand-oblation-research.md`](docs/11-direct-emptyhand-oblation-research.md) — preferred direct delivery with zero Carry and original basket interaction; upstream code proof and staged validation.
- [`docs/12-emptyhand-implementation-options-and-poc.md`](docs/12-emptyhand-implementation-options-and-poc.md) — Lua PoC, tests, sys-botbase vs IPS and remaining bytecode/LayeredFS deployment work.

## Important status note

The public `SV-Script-RE` material used to recover symbol semantics describes 3.0.1-era script data. The uploaded Violet 4.0.0 ELF has the same commonly used 16-hex Build ID prefix as 3.0.1 (`709BFD6611529864`), but this alone does **not** prove every Lua resource byte is identical. The patch therefore verifies hash-name anchors before modifying a user-extracted script.

**2026-10-24 update:** The 4.0.0 inner virtual path is now externally documented as `script/lua/bin/release/main/main.blua` (pokeldn Scarlet 4.0.0 analysis), and the extracted payload is Lua **5.4 bytecode**. The actual user-owned Violet 4.0.0 resource must still be checked locally. See [docs/13](docs/13-v400-blua-bytecode-merge-trinity.md). Do not confuse the flattened TRPFD pack name with this inner path.

## Safety / scope

This repository is intended for reverse engineering, offline testing, local multiplayer research, and mod-development work. Multiplayer authority behavior is documented separately; do not assume a local memory mutation is network-safe.

## Experimental Violet 4.0.0 Raid MaxHP IPS32 branch

An **offline development preview** IPS32 is included at [`patches/ips32/SV400_MaxHP_Source1_DEV/`](patches/ips32/SV400_MaxHP_Source1_DEV/). It redirects the damage record write and substitutes target MaxHP when the observed attacker index is 1. The binary has been generated and statically checked against the exact Violet 4.0.0 ELF, **but not run-tested in Eden**.

**Warning:** this is **not a verified raid-only patch**. Source index 1 may occur in ordinary battles, and zero-damage events may be affected. Do not enable in public multiplayer or normal gameplay. See [`docs/15-v400-raid-maxhp-ips32-dev.md`](docs/15-v400-raid-maxhp-ips32-dev.md) for exact limitations, install instructions and reproducible build steps. This experiment is separate from Ogre Oustin' Lua research.
