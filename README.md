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

## Documentation

- [`docs/01-elf-4.0.0.md`](docs/01-elf-4.0.0.md) — 4.0.0 ELF layout and native Ojama findings.
- [`docs/02-lua-state-and-functions.md`](docs/02-lua-state-and-functions.md) — class map, 3×4 fruit state and important functions.
- [`docs/03-network-protocol.md`](docs/03-network-protocol.md) — packet IDs 506/507/511/513 and authority flow.
- [`docs/04-lua-patch-design.md`](docs/04-lua-patch-design.md) — exact monkey-patch points and Smart Balloon / Auto Deposit / Instant Round design.
- [`docs/05-layeredfs-trinity.md`](docs/05-layeredfs-trinity.md) — Trinity and Atmosphère/LayeredFS packaging workflow.
- [`docs/06-runtime-validation.md`](docs/06-runtime-validation.md) — validation matrix for 4.0.0, especially multiplayer.
- [`docs/07-sources.md`](docs/07-sources.md) — public source references used during analysis.

## Important status note

The public `SV-Script-RE` material used to recover symbol semantics describes 3.0.1-era script data. The uploaded Violet 4.0.0 ELF has the same commonly used 16-hex Build ID prefix as 3.0.1 (`709BFD6611529864`), but this alone does **not** prove every Lua resource byte is identical. The patch therefore verifies hash-name anchors before modifying a user-extracted script.

The exact 4.0.0 TRPFS virtual path of the main Lua resource must be confirmed from a real 4.0.0 RomFS / `data.trpfd` in Trinity File Explorer. Public Trinity documentation establishes the TRPFS workflow and `script` as a recognized RomFS root, but the repository intentionally does not pretend an unverified `script/main.lua` path is proven.

## Safety / scope

This repository is intended for reverse engineering, offline testing, local multiplayer research, and mod-development work. Multiplayer authority behavior is documented separately; do not assume a local memory mutation is network-safe.
