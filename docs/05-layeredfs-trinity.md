# Trinity / LayeredFS packaging workflow

## What is verified

Trinity Mod Loader is designed for Game Freak's TRPFS/TRPFD virtual filesystem. Its current public README describes the intended authoring workflow as:

1. point Trinity at a valid RomFS;
2. extract the target resource with Trinity File Explorer;
3. keep the resource's virtual path inside the mod folder;
4. add the folder/ZIP as a mod;
5. Apply Mods;
6. install the generated LayeredFS output.

For Atmosphère, generated `romfs` belongs under:

```text
sd:/atmosphere/contents/<TitleID>/romfs/...
```

Pokémon SV title IDs:

```text
Scarlet: 0100A3D008C5C000
Violet : 01008F6008C5E000
```

Therefore the Violet installation root is:

```text
sd:/atmosphere/contents/01008F6008C5E000/
```

## Confirmed Violet 4.0.0 Lua pack names

A user-supplied Violet 4.0.0 `arc/data.trpfd` has now been parsed directly as Trinity's FlatBuffer `FileDescriptor` structure.

The primary main-script pack is confirmed as:

```text
arc/scriptluabinreleasemainmain.blua.trpak
```

Descriptor metadata:

```text
Pack index : 14659
Pack size  : 2,255,432 bytes
File count : 1
```

The dynamic main-script pack is:

```text
arc/scriptluabinreleasemain_dynamicmain_dynamic.blua.trpak
```

Descriptor metadata:

```text
Pack index : 14660
Pack size  : 551,344 bytes
File count : 1
```

Other confirmed Lua packs in the same descriptor:

```text
14658  arc/scriptluabinreleasedll_utildll_util.blua.trpak       17,736 bytes
14657  arc/scriptluabinreleasedll_stadiumdll_stadium.blua.trpak 22,976 bytes
14656  arc/scriptluabinreleasedll_picnicdll_picnic.blua.trpak    8,184 bytes
14655  arc/scriptluabinreleasedll_danbattledll_danbattle.blua.trpak 33,808 bytes
```

The Ogre Oustin classes are expected in the primary `main` package.

## Pack name is not the final loose-resource path

The confirmed string above is the **TRPFD pack name**. Do not rewrite it into a guessed loose path such as `script/main.lua`.

Each confirmed main pack reports `FileCount = 1`. After the `.trpak` is extracted, its `PackedArchive` must be inspected to identify the single contained resource hash/path. The entry may be Oodle-compressed.

Therefore the final Trinity input path should be taken from the actual extracted inner resource, not inferred from the flattened pack name.

## Why `data.trpfs` is required

`data.trpfd` provides pack names, pack sizes and file-to-pack mappings. The physical byte offsets of packs are stored in `data.trpfs`.

Trinity's ONEFILE reader does this:

```text
read 16-byte header
seek header.offset
parse FileSystem FlatBuffer
```

The structures are:

```text
OneFileHeader
├─ magic  : UInt64
└─ offset : Int64

FileSystem
├─ FileHashes  : UInt64[]
└─ FileOffsets : UInt64[]
```

The physical extraction algorithm is:

```text
packHash   = FNV1a64(packName)
fileIndex  = index(FileSystem.FileHashes, packHash)
packOffset = FileSystem.FileOffsets[fileIndex]
packSize   = TRPFD.PackInfo[packIndex].FileSize
read data.trpfs[packOffset : packOffset + packSize]
```

`tools/extract_trpak.py` implements this directly.

Example after obtaining the matching `data.trpfs`:

```bash
python tools/extract_trpak.py \
  data.trpfd \
  data.trpfs \
  build/main.blua.trpak
```

The default `--pack` is the confirmed Violet 4.0.0 primary main pack.

## Generate the patched Lua

After extracting/decompressing the single inner Lua resource, verify that it contains these anchors:

```text
C6D182891100F211D
FCE25070892D46E56
F466EB120F65C4DF8
F5F3E9041FE44C3C6
CE506B90C88D90C92
C9FD31BF01E130013
CC07CA97E7F9D78F4
```

Then:

```bash
python tools/patch_main_lua.py \
  extracted/main.lua \
  build/main.lua
```

The patcher prints SHA-256 for input/output and refuses to patch when the expected anchors are absent.

Do not use `--force` simply to bypass a version mismatch.

## Trinity folder / ZIP

An `info.toml` supported by Trinity uses:

```toml
display_name = "Ogre Oustin Lua Patch"
author_name = "969981"
version = "0.1.0-experimental"
description = "Smart Balloon, Auto Deposit and Instant Round research patch. Requires a user-extracted compatible SV main Lua."
```

Once Trinity File Explorer has revealed the **actual inner resource path**, stage the patched resource at that exact path:

```text
Ogre_Oustin_Trinity/
├─ info.toml
└─ <exact extracted resource path>
```

Add this folder with **Add Folder Mod** and run **Apply Mods**.

Do not add an extra `romfs` wrapper inside the Trinity input folder unless the tool version explicitly requests one.

## Trinity output

The generated output should conceptually contain:

```text
output/
└─ romfs/
   ├─ arc/
   │  └─ data.trpfd
   └─ ... loose/rebuilt resource override files ...
```

The exact generated file set depends on Trinity version and other merged mods.

## Atmosphère install

For Violet:

```text
sd:/atmosphere/contents/01008F6008C5E000/
└─ romfs/
   ├─ arc/
   │  └─ data.trpfd
   └─ ... generated override files ...
```

For Scarlet, use `0100A3D008C5C000` and resources extracted from the matching Scarlet build.

## Conflict handling

If another SV mod changes the same main Lua resource, both mods replace one large resource and cannot be safely merged by file priority alone.

Use this sequence instead:

1. extract the desired compatible base script;
2. apply the other script edits;
3. run `patch_main_lua.py` against that already-modified script;
4. package only the resulting final script resource.
