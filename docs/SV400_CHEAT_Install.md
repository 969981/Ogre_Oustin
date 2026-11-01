# SV 4.0.0: 65535 damage-record cheat TXT deployment

Four standalone cheat TXT ZIPs have been added to the existing four IPS32 ZIPs (Scarlet/Violet x Atmosphere/Ryujinx).

**Experimental, offline only.** Not a proven one-hit KO. Violet's original `main+0x01536214` was statically checked as `LDRH W25,[SP,#0x9C]`. The code changes an intermediate 16-bit damage-record instruction to `MOVZ W25,#0xFFFF` after verifying the original word. It is NOT boss-only or raid-only. Other game logic may cap or overwrite damage. Scarlet's RVA and original instruction have NOT been checked against its own original executable, so ALL Scarlet assets carry `CANDIDATE` and could crash or be ineffective. Back up save data, do not use online or in public multiplayer.

## Code (same for both games, different file names)

```text
[SV 4.0.0 Damage Record 65535 EXPERIMENTAL]
14050000 01536214 79413BF9
04000000 01536214 529FFFF9
20000000
```

First code line compares the original 32-bit word in Main NSO; next writes the MOV instruction only if equal; final line ends the conditional block. The guard does not establish Scarlet correctness.

| Version | Game Title ID | Cheat TXT name (8-byte BID) | Full main NSO Build ID (20 bytes) |
| --- | --- | --- | --- |
| Scarlet 4.0.0 | `0100A3D008C5C000` | `421C5411B487EB4D.txt` | `421C5411B487EB4D049DD065FEC9547773E8E598` |
| Violet 4.0.0 | `01008F6008C5E000` | `709BFD6611529864.txt` | `709BFD66115298640155FCC4979DBA151C7CC79A` |

## Install ZIPs

Four packages:
- `Pokemon_Scarlet_4.0.0_Atmosphere_65535_CHEAT_CANDIDATE.zip`
- `Pokemon_Scarlet_4.0.0_Ryujinx_65535_CHEAT_CANDIDATE.zip`
- `Pokemon_Violet_4.0.0_Atmosphere_65535_CHEAT.zip`
- `Pokemon_Violet_4.0.0_Ryujinx_65535_CHEAT.zip`

### Switch / Atmosphere

Extract the selected Atmosphere ZIP to the SD root; the actual paths are:

```text
atmosphere/contents/0100A3D008C5C000/cheats/421C5411B487EB4D.txt
atmosphere/contents/01008F6008C5E000/cheats/709BFD6611529864.txt
```

**If you already have a cheats/<BID>.txt, back it up and MERGE the new cheat block; extracting over the old file would overwrite other cheats.** Restart game fully to apply/remove. Use compatible cheat manager to enable.

### Ryujinx / Ryubing

Extract the selected Ryujinx ZIP into the emulator's portable data folder containing `mods/`. Result:

```text
mods/contents/0100A3D008C5C000/SV400_Always65535Damage_Cheat/cheats/421C5411B487EB4D.txt
mods/contents/01008F6008C5E000/SV400_Always65535Damage_Cheat/cheats/709BFD6611529864.txt
```

Nonportable: right-click the game -> Open Mods Directory, copy the `SV400_Always65535Damage_Cheat/cheats/<BID>.txt` folder under that game directory. Then use **Manage Cheats**, not Manage Mods, to enable the selected code (as supported by the emulator build). Restart the game.

**DO NOT enable the older IPS32 and this cheat together:** both target the same RVA and interfere with diagnosis. Disabling the cheat after it has already rewritten the instruction does not immediately restore the original game code; fully close and restart the game.

Unit tests verify ZIP paths and conditional cheat syntax, NOT gameplay/HP/win/reward success. See [Atmosphere cheat VM reference](https://github.com/Atmosphere-NX/Atmosphere/blob/master/docs/features/cheats.md) and [Ryubing guide](https://docs.ryujinx.app/guides/setup-guide/).
