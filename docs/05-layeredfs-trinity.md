# Trinity / LayeredFS packaging workflow

## What is verified

Trinity Mod Loader is designed for Game Freak's TRPFS/TRPFD virtual filesystem. Its current public README describes the intended authoring workflow as:

1. point Trinity at a valid RomFS;
2. extract the target resource with Trinity File Explorer;
3. keep the resource's RomFS-relative / virtual path inside the mod folder;
4. add the folder/ZIP as a mod;
5. Apply Mods;
6. install the generated LayeredFS output.

For Atmosphère, a mod containing `romfs` belongs under:

```text
sd:/atmosphere/contents/<TitleID>/romfs/...
```

Pokémon title IDs used by public SV modding documentation:

```text
Scarlet: 0100A3D008C5C000
Violet : 01008F6008C5E000
```

Therefore the Violet installation root is:

```text
sd:/atmosphere/contents/01008F6008C5E000/
```

## TRPFD detail that matters

SV resources are not correctly described as “just copy a random file beside the executable”. Trinity builds/updates the TRPFD descriptor used to map virtual resources to the LayeredFS override.

A modern equivalent tool (`TrpfdUpdater`) documents the resulting concept explicitly: a merged target contains loose RomFS resources plus a generated:

```text
romfs/arc/data.trpfd
```

that references them.

That is why this project distinguishes:

- **Trinity mod input layout** — virtual/RomFS-relative resources plus `info.toml`;
- **Trinity generated output** — a complete `romfs` override including the rebuilt descriptor;
- **Atmosphère install layout** — the generated `romfs` copied under the game's title ID.

## Main-Lua path: do not guess

The uploaded 4.0.0 ELF cannot reveal the TRPFS path of the Lua resource. Public tooling recognizes `script` as an SV RomFS root, but that does not by itself prove that the required 4.0.0 resource is exactly `script/main.lua`.

The correct workflow is:

1. dump/extract Pokémon Violet **4.0.0 RomFS**;
2. open it in Trinity File Explorer / Trinity Mod Loader;
3. browse or search the `script` root;
4. extract the candidate main script;
5. verify that its text contains these hash anchors:

```text
C6D182891100F211D
FCE25070892D46E56
F466EB120F65C4DF8
F5F3E9041FE44C3C6
CE506B90C88D90C92
```

6. preserve the exact path shown by Trinity when packaging the patched version.

If Trinity reports the file as `script/main.lua`, then the mod folder is:

```text
Ogre_Oustin_Trinity/
├─ info.toml
└─ script/
   └─ main.lua        <- patched user-extracted file
```

If the descriptor reports a different path, use that exact path instead.

## Generate the patched file

Example:

```bash
python tools/patch_main_lua.py \
  extracted/main.lua \
  build/main.lua
```

The tool prints SHA-256 for input/output and refuses to patch when expected hash anchors are absent.

Do not use `--force` simply to bypass a version mismatch. Use it only after manually confirming that the relevant 4.0.0 class/method semantics are still correct.

## Trinity folder/ZIP

An `info.toml` supported by Trinity uses fields represented by its current `ModData` model:

```toml
display_name = "Ogre Oustin Lua Patch"
author_name = "969981"
version = "0.1.0-experimental"
description = "Smart Balloon, Auto Deposit and Instant Round research patch. Requires a user-extracted compatible SV main Lua."
```

After placing the patched Lua at the exact virtual path:

```text
Ogre_Oustin_Trinity/
├─ info.toml
└─ <exact virtual path from Trinity File Explorer>
```

add the folder with **Add Folder Mod**, or ZIP the folder contents and add the archive.

The mod archive should represent the resource layout, not contain an extra `romfs` wrapper when used as a Trinity input pack.

## Trinity output

Set a clean output directory and run **Apply Mods**.

Expected conceptual result:

```text
output/
└─ romfs/
   ├─ arc/
   │  └─ data.trpfd
   └─ script/
      └─ ... patched Lua at its resolved path ...
```

The exact set of generated files depends on Trinity version and what other mods are merged.

## Atmosphère install

For Violet:

```text
sd:/atmosphere/contents/01008F6008C5E000/
└─ romfs/
   ├─ arc/
   │  └─ data.trpfd
   └─ ... generated override files ...
```

For Scarlet, use `0100A3D008C5C000` and a script extracted from the matching Scarlet version. Do not assume a Violet-generated descriptor can be reused blindly for Scarlet.

## Emulator-style LayeredFS

Emulators/loaders differ in the parent mod directory, but the payload remains a normal `romfs` tree. For Yuzu-style loaders it is commonly:

```text
.../load/<TitleID>/Ogre_Oustin/romfs/...
```

Use the emulator's “Open Mod Data/Directory” action rather than guessing its global data path.

## Conflict handling

If another SV mod modifies the same script resource, the mods cannot be safely combined by simply selecting both copies and hoping for a field-level merge. They both replace the same large Lua resource.

For such a conflict:

1. choose the desired base version of the script;
2. apply the other script changes first;
3. run `patch_main_lua.py` against that already-modified base;
4. package only the resulting final script resource.

Trinity can resolve file-level priority, but it cannot semantically merge two independent edits inside one Lua file.
