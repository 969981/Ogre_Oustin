# Public source references

This repository does not redistribute Nintendo/Game Freak game assets or the original SV main Lua. The reverse-engineering notes are based on user-supplied binary analysis plus public code/tooling references.

## Script reverse engineering

### Martmists-GH/SV-Script-RE

https://github.com/Martmists-GH/SV-Script-RE

Used to recover generated Lua/Haxe class/function semantics and hash-named call chains.

Important files referenced during Ogre Oustin analysis include:

```text
decompiled/C6D182891100F211D.lua   OniballoonAppliSceneManager-like scene manager
decompiled/CA2A924A55DC1CE8A.lua  core game model/coordinator
decompiled/C9FD31BF01E130013.lua   OniballoonHudModel-like fruit model
decompiled/CC07CA97E7F9D78F4.lua   FruitsViewSupporter-like concrete matrix
decompiled/CE6DE953128959840.lua   OniballoonNetMediator

decompiled/C202B78F79F22D60D.lua  generic/network manager send wrappers
native/c2382B286.lua               native GetKinomi packet userdata stub
native/c511BF168.lua               native Oblation packet userdata stub
```

The repository README explicitly states that its target was the latest game version at the time, **3.0.1**. Consequently, identifiers recovered from it are treated as 3.0.1-era semantics until checked against a user-extracted 4.0.0 script.

Its `tools/test_hash.py` documents the naming convention used by the RE project:

- 32-bit `cXXXXXXXX` / `fXXXXXXXX` style names use CRC32;
- 64-bit class/static/function hashes use FNV-1a 64-bit in the helper.

## Trinity / TRPFS tooling

### pkZukan/gftool

https://github.com/pkZukan/gftool

The current monorepo contains Trinity Mod Loader and Trinity File Explorer.

Relevant documentation/source:

```text
TrinityModLoader/README.md
TrinityModLoader/Models/ModEntry/ModEntry.cs
```

The README describes creating a mod by extracting resources with Trinity File Explorer, preserving their layout, adding the folder to Trinity and applying mods to generate LayeredFS output.

`ModEntry.cs` exposes the `info.toml` metadata fields currently represented by the loader:

```text
display_name
author_name
version
description
```

### Aqua-0/TrpfdUpdater

https://github.com/Aqua-0/TrpfdUpdater

Useful independent documentation of the modern loose-file + `romfs/arc/data.trpfd` workflow and known SV RomFS roots such as `script`.

## LayeredFS / Atmosphère

### NH Switch Guide — Game modding with LayeredFS

https://switch.hacks.guide/extras/game_modding

Documents the standard Atmosphère layout:

```text
sd:/atmosphere/contents/<title_id>/romfs
```

## SV mod packaging tutorials

### Inidar1/Switch-Pokemon-Modding-Tutorials

https://github.com/Inidar1/Switch-Pokemon-Modding-Tutorials

Public tutorial material documents Trinity packaging conventions and the Pokémon SV title IDs:

```text
Scarlet: 0100A3D008C5C000
Violet : 01008F6008C5E000
```

It also distinguishes a Trinity input pack from the final `romfs` output installed under Atmosphère/emulator mod directories.

## Data/schema references

### kwsch/pkNX

https://github.com/kwsch/pkNX

Contains Scarlet/Violet data schemas including Ogre Oustin game-base parameter schema work.

### Xzonn/PokemonSV-pkNX

https://github.com/Xzonn/PokemonSV-pkNX

Contains public extracted/processed data examples used as a cross-check for Ogre Oustin parameters. Values from those public data files are reference data only and are not claimed to have been extracted from the user-supplied 4.0.0 ELF.

## 4.0.0 ELF source

The detailed 4.0.0 ELF offsets in `docs/01-elf-4.0.0.md` came from static analysis of the `Violet4.0.0.elf` supplied directly by the repository owner during the research session.

Identity recorded during analysis:

```text
GNU Build ID: 709bfd66115298640155fcc4979dba151c7cc79a
```

The binary itself is not committed to this repository.
