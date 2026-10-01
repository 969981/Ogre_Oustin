# Trinity pack assembly

This directory contains metadata only. The original Pokémon SV Lua resource is intentionally not included.

## Confirmed Violet 4.0.0 source pack

The supplied Violet 4.0.0 `arc/data.trpfd` confirms the primary main-script pack as:

```text
arc/scriptluabinreleasemainmain.blua.trpak
```

Descriptor metadata:

```text
Pack index : 14659
Pack size  : 2,255,432 bytes
File count : 1
```

The dynamic companion pack is:

```text
arc/scriptluabinreleasemain_dynamicmain_dynamic.blua.trpak
```

Do not confuse these flattened TRPFD **pack names** with the final loose inner-resource path. The exact Trinity mod path is determined after extracting the single resource contained in the `.trpak`.

## Extract the pack

With matching 4.0.0 files:

```text
arc/data.trpfd
arc/data.trpfs
```

run:

```bash
python tools/extract_trpak.py \
  data.trpfd \
  data.trpfs \
  build/main.blua.trpak
```

Then inspect/extract the single `PackedArchive` entry with Trinity File Explorer. If its compression flag is not `-1`, Trinity uses Oodle to decompress it.

## Patch the extracted main Lua

After recovering the inner main Lua:

```bash
python tools/patch_main_lua.py <extracted-main.lua> <patched-main.lua>
```

The patcher checks the Oniballoon hash anchors before modifying the file.

## Build a Trinity folder mod

1. Copy `info.toml` into a clean staging folder.
2. Recreate the **exact inner resource path shown by Trinity File Explorer**.
3. Place the patched resource at that path.
4. Add the staging folder using Trinity Mod Loader's **Add Folder Mod**.
5. Apply Mods.
6. Install the generated `romfs` under the matching title ID.

Violet:

```text
sd:/atmosphere/contents/01008F6008C5E000/romfs/
```

Scarlet:

```text
sd:/atmosphere/contents/0100A3D008C5C000/romfs/
```

See `docs/05-layeredfs-trinity.md` and `docs/08-trpfd-4.0.0-main-lua.md` for the binary mapping details.
