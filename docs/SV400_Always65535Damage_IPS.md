# Pokemon Violet 4.0.0 — unconditional 65535-damage IPS32

**Experimental, offline-only.** One AArch64 instruction is replaced; no raid/player/boss checks.

| Field | Value |
|---|---|
| ELF SHA256 | `d17403eaa9d844db82f647fd2f1518806b10c0518d53602fc0ac1766298fdba0` |
| Game | Pokemon Violet 4.0.0 |
| main NSO Build ID | `709bfd66115298640155fcc4979dba151c7cc79a` |
| RVA | `main+0x1536214` |
| Original | `LDRH W25,[SP,#0x9C]` = bytes `f9 3b 41 79` |
| Patched | `MOV W25,#0xFFFF` = bytes `f9 ff 9f 52` |
| IPS32 offset | `0x1536314` = RVA + `0x100` (decompressed NSO header) |
| ELF file offset | RVA + `0x8D8` (optional verifier only) |

`main+0x1536218` subsequently writes `W25` as a 16-bit halfword. Another original branch at `main+0x1536268..0x1536270` can still select `min(w0,w25)`; other stages may cap or overwrite damage. **One-hit defeat, normal reward processing, and compatibility are not established.** This affects every execution of the instruction, not just raids.

## Build

```bash
python -m unittest discover -s tests -p 'test_sv400_raid_damage_ips.py' -v
python tools/build_sv400_raid_damage_ips.py --output-dir dist
```

Optional offline check with your own unmodified ELF:

```bash
python tools/build_sv400_raid_damage_ips.py --elf Violet4.0.0.elf --output-dir dist
```

## Install / Remove

Extract the release ZIP at SD card root so the IPS is at:

```text
atmosphere/exefs_patches/SV400_Always65535Damage/709bfd66115298640155fcc4979dba151c7cc79a.ips
```

Remove `atmosphere/exefs_patches/SV400_Always65535Damage` to uninstall. Back up saves before testing. Test only in isolated/local offline games, not public multiplayer. This patch does **not** target Scarlet or other versions.

## Ryujinx 1.3.3 build-id filename compatibility (2026-11-01)

The 1.3.3 user log detected the mod and the correct Violet 4.0.0 Build ID, but not an IPS match. Earlier generator releases used a lowercase filename. Ryujinx code paths use uppercased NSO Build IDs and strict string equality for matching, so IPS filenames must be uppercase for compatibility with such builds. Release v1.0.3 and later use `709BFD66115298640155FCC4979DBA151C7CC79A.ips`. The IPS content is unchanged; matching and gameplay effects must be tested separately.
