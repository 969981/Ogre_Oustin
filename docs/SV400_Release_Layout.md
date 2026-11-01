# Scarlet / Violet 4.0.0: four separate IPS32 release packages

The release contains four separately installable ZIP archives:

| Game | Switch Atmosphere | Ryujinx / Ryubing |
| --- | --- | --- |
| Scarlet 4.0.0 | Pokemon_Scarlet_4.0.0_Atmosphere_65535_CANDIDATE.zip | Pokemon_Scarlet_4.0.0_Ryujinx_65535_CANDIDATE.zip |
| Violet 4.0.0 | Pokemon_Violet_4.0.0_Atmosphere_65535.zip | Pokemon_Violet_4.0.0_Ryujinx_65535.zip |

WARNING: The Scarlet version is an UNVERIFIED CANDIDATE. Its Build ID is known, but the patch RVA and original instruction have NOT been validated against Scarlet's own 4.0.0 main NSO. The same offset is assumed from Violet. An invalid patch can crash the game. Do not present it as a working patch.

Violet's original instruction at main+0x1536214 is statically verified. Neither game's actual 65535-damage/one-hit KO outcome has been verified. This changes one instruction unconditionally, NOT raid-only. Further logic may clamp the damage. Back up saves and use only in isolated/offline experiments, never online or public multiplayer.

Build IDs:
- Scarlet 4.0.0: Title ID 0100A3D008C5C000; NSO Build ID 421C5411B487EB4D049DD065FEC9547773E8E598
- Violet 4.0.0: Title ID 01008F6008C5E000; NSO Build ID 709BFD66115298640155FCC4979DBA151C7CC79A

Atmosphere ZIP extraction root: SD card root.
Install path: atmosphere/exefs_patches/SV400_Always65535Damage/<FULL_BUILD_ID>.ips

Ryujinx / Ryubing portable ZIP extraction root: emulator portable folder containing mods/.
Install path: mods/contents/<TITLE_ID>/SV400_Always65535Damage/exefs/<FULL_BUILD_ID>.ips
For non-portable installs, use the application's Open Mods Directory instead. Enable the mod, exit the game completely, and restart. Do not enable duplicate IPS packages from both the Atmosphere and Ryujinx paths simultaneously.

IPS32 single record: offset 0x1536314 = main+0x1536214 + NSO 0x100, record length 4, instruction bytes F9 FF 9F 52 (MOV W25,#0xFFFF).

Build with:
    python tools/build_sv400_raid_damage_ips.py --output-dir dist
    python tools/package_sv400_four.py --output-dir dist
Test with:
    python -m unittest discover -s tests -p 'test_sv400_*.py' -v
