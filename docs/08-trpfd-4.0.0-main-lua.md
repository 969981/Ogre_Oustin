# Violet 4.0.0 TRPFD: confirmed main Lua packs

## Input

This note is based on a user-supplied Pokémon Violet 4.0.0 `arc/data.trpfd`.

The descriptor was parsed as the FlatBuffer structure used by Trinity/gftool:

```text
FileDescriptor / CustomFileDescriptor
├─ FileHashes : UInt64[]
├─ PackNames  : string[]
├─ FileInfo   : FileInfo[]
└─ PackInfo   : PackInfo[]
```

`PackInfo` contains:

```text
FileSize  : UInt64
FileCount : UInt64
```

The uploaded descriptor contains:

```text
PackNames : 16,112
FileHashes: 273,862
```

## Confirmed Lua packs

The following entries exist verbatim in `PackNames`:

| Pack index | Pack name | Size | File count |
|---:|---|---:|---:|
| 14659 | `arc/scriptluabinreleasemainmain.blua.trpak` | 2,255,432 bytes | 1 |
| 14660 | `arc/scriptluabinreleasemain_dynamicmain_dynamic.blua.trpak` | 551,344 bytes | 1 |
| 14658 | `arc/scriptluabinreleasedll_utildll_util.blua.trpak` | 17,736 bytes | 1 |
| 14657 | `arc/scriptluabinreleasedll_stadiumdll_stadium.blua.trpak` | 22,976 bytes | 1 |
| 14656 | `arc/scriptluabinreleasedll_picnicdll_picnic.blua.trpak` | 8,184 bytes | 1 |
| 14655 | `arc/scriptluabinreleasedll_danbattledll_danbattle.blua.trpak` | 33,808 bytes | 1 |

For Ogre Oustin research, the primary target is:

```text
arc/scriptluabinreleasemainmain.blua.trpak
```

The secondary target is:

```text
arc/scriptluabinreleasemain_dynamicmain_dynamic.blua.trpak
```

The Oniballoon classes recovered from the 3.0.1-era main script are expected in the primary `main` package, but this should still be verified after extracting the 4.0.0 package payload.

## Important distinction: pack path vs inner resource path

`arc/scriptluabinreleasemainmain.blua.trpak` is the **TRPFD pack name**. It is not yet proof that the final loose Trinity resource path is literally the same flattened string.

Each of these packs reports `FileCount = 1`, so after extracting the `.trpak` we only need to identify one contained resource. Trinity's `PackedArchive` structure stores the contained file hash and `PackedFile` record; the inner file may be Oodle-compressed.

Do not manufacture a loose path such as `script/main.lua` from the pack name. Preserve the path/hash resolved by Trinity after the pack is opened.

## Why `data.trpfs` is still needed

`data.trpfd` describes pack names and sizes, but not the physical pack offsets used to read `data.trpfs`.

Trinity/gftool reads the first 16-byte ONEFILE header from `data.trpfs`:

```text
struct OneFileHeader {
    UInt64 magic;
    Int64  offset;
}
```

It seeks to `header.offset` and deserializes a `FileSystem` FlatBuffer:

```text
FileSystem
├─ FileHashes  : UInt64[]
└─ FileOffsets : UInt64[]
```

Extraction is then:

```text
packHash   = FNV1a64(packName)
fileIndex  = index(FileSystem.FileHashes, packHash)
packOffset = FileSystem.FileOffsets[fileIndex]
packSize   = TRPFD.PackInfo[packIndex].FileSize
read data.trpfs[packOffset : packOffset + packSize]
```

For the primary main script pack the size is already known to be `2,255,432` bytes. The missing value is the corresponding physical offset from `data.trpfs`.

## Next step

Provide the matching Violet 4.0.0:

```text
arc/data.trpfs
```

Then run `tools/extract_trpak.py` or Trinity File Explorer to extract:

```text
arc/scriptluabinreleasemainmain.blua.trpak
```

After that:

1. deserialize the single `PackedArchive` entry;
2. identify its inner resource hash/path;
3. Oodle-decompress if required;
4. confirm the 4.0.0 Lua hash anchors;
5. apply `patches/lua/ogre_oustin_patch.lua`;
6. rebuild/package with the exact Trinity virtual path.
