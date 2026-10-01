# Trinity pack assembly

This directory contains metadata only. The original Pokémon SV Lua resource is intentionally not included.

## Build a folder mod

1. Extract the 4.0.0 main Lua with Trinity File Explorer.
2. Verify/patch it with:

```bash
python tools/patch_main_lua.py <extracted-main.lua> <patched-main.lua>
```

3. Copy `info.toml` into a new staging folder.
4. In that staging folder, recreate the **exact virtual path shown by Trinity File Explorer** and place the patched Lua there.

Example **only if Trinity confirms `script/main.lua`**:

```text
Ogre_Oustin_Trinity/
├─ info.toml
└─ script/
   └─ main.lua
```

5. Add the staging folder using Trinity Mod Loader's **Add Folder Mod** and Apply Mods.
6. Install the generated `romfs` under the correct title ID.

Violet:

```text
sd:/atmosphere/contents/01008F6008C5E000/romfs/
```

Scarlet:

```text
sd:/atmosphere/contents/0100A3D008C5C000/romfs/
```

Do not substitute `script/main.lua` merely because it is shown in this example; the exact 4.0.0 resource path must be confirmed from the descriptor.
