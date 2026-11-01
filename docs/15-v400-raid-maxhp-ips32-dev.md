# Violet 4.0.0 MaxHP IPS32 · Offline Developer Preview

**Scope:** Game version 4.0.0, Title ID `01008F6008C5E000`, Build ID `709BFD66115298640155FCC4979DBA151C7CC79A`.

**Warning:** This is a real IPS32 code patch, statically verified with LLVM, but not a fully validated Raid-only mod. Do not use in public matchmaking or ordinary gameplay; test only on a backed-up offline save, disable immediately afterward.

## What it does

At `main+0x1536218`, redirects the original `strh w25,[x28,#4]!` into a 28-byte padded code location `main+0x420BE4`, then returns to `main+0x153621C`. The trampoline tests whether the **observed attacker entity index equals 1** (`*(SP+0x90)+0x50`), and if so loads target maxHP from `X24+0x58` into `W25` before executing the original STRH.

Registers W8 and W27 remain intact; W9 and W10 are changed and are overwritten by subsequent original code. Later native damage clipping, lethal checks and HP consumption are preserved.

**Critical limitations:**

- This index check is **not** proof of Raid mode or local player ownership. Ordinary battles with attacker index 1 could be affected.
- There is no zero-damage filter; immunity/status effects or misses that reach this path can be altered.
- All other Raid bosses, NPC, guest and shield behaviors are untested. Some may fail to trigger.
- This IPS has been checked against the original ELF but has **not** been validated by running it in Eden.
- The original *manual GDB experiment* did confirm Mewtwo HP `17650 → 0`, native victory/capture screen and rewards entered bag. The IPS does not inherit that runtime test automatically.

## Files

- [53-byte IPS32](../patches/ips32/SV400_MaxHP_Source1_DEV/709BFD66115298640155FCC4979DBA151C7CC79A.ips)
- [Rebuild script](../tools/build_sv400_raid_maxhp_ips32.py)
- [Tests](../tests/test_sv400_raid_maxhp_ips32.py)

IPS SHA256: `b7d03d97542f95f27383ff1ceb8e9b8eb39c33ed7535be520be07e1cbc581e84`.
Original ELF SHA256: `d17403eaa9d844db82f647fd2f1518806b10c0518d53602fc0ac1766298fdba0`.

## Installation

In Eden, right-click Violet → Open Mod Data Location. Copy the folder `SV400_MaxHP_Source1_DEV` containing `exefs/<BuildID>.ips` from the ZIP's `Eden_Mod_Data_Location` directory. Enable under Configure Game → Add-Ons and restart. Verify IPS32 support for the installed Eden build. Disable and restart after one offline test.

For Atmosphère, install `atmosphere/exefs_patches/SV400_MaxHP_Source1_DEV/<BuildID>.ips`. It uses IPS32 offset convention (0x100-byte NSO header plus text RVA).

## Rebuild and verify

Use your own extracted original ELF, not a Nintendo executable included in this repository:

```sh
python tools/build_sv400_raid_maxhp_ips32.py --elf /path/to/Violet4.0.0.elf --out /tmp/709BFD66115298640155FCC4979DBA151C7CC79A.ips
SV400_ELF=/path/to/Violet4.0.0.elf python -m unittest discover -s tests -p 'test_sv400_raid_maxhp_ips32.py'
```

**Before a general release:** Recover reliable `isRaid`, `sourceLocalPlayer`, `targetRaidBoss`, and positive damage gates, then reimplement with enough trampoline space or a dynamic ExLaunch hook and perform negative regression tests. Do not rename this preview as a universal Raid patch.
