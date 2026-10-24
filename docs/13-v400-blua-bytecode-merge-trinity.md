# 13 — 朱紫 4.0.0 main.blua：格式确认、免反编译合并和 Trinity 部署

**研究日期**：2026-10-24  
**范围**：Pokémon Violet 4.0.0 打鬼祭空手交付。  
**状态**：独立标准 Lua 5.4 运行库的模拟字节码组合已成功；尚未取得真实 Violet 4.0.0 main.blua 做兼容测试，也未完成 Switch 实机验证。

## 1. 关键新发现：不需要先反编译整个 main.blua

此前 docs/05、08、12 无法确认具体脚本文件格式与准确内层路径。现有公开的 pokeldn 对 4.0.0 的研究已明确：

- 原始虚拟路径：script/lua/bin/release/main/main.blua。
- 属于标准 **Lua 5.4 字节码（bytecode）**，包含 **30,829 个顶层函数原型**。
- 其内容在 TRPFS 中由 Oodle 压缩储存；pack 名是 arc/scriptluabinreleasemainmain.blua.trpak。
- 对方发布的 SHA256 c1a4f4e2625912cf0b739a642a79ba3357df0557a544b92da22a6cb139de2815 是 **Scarlet 4.0.0** 主脚本样本；不应直接作为 Violet 文件的固定哈希。
- 来源：[pokeldn SV Union Circle 文档](https://decryptu.github.io/pokeldn/sv_union_circle.html)、[其开源读取器](https://github.com/decryptu/pokeldn/blob/main/tools/switch/trpfs_read.py)、[FlatBuffer/Oodle 解析](https://github.com/decryptu/pokeldn/blob/main/tools/switch/trpfs.py)。

Lua 官方编译器 **luac5.4** 支持在一次调用中混合源文件与已经编译好的 Lua 5.4 字节码文件，生成依次运行的组合字节码。官方源码中的 combine() 会把现有代码作为外层包装器子原型，处理各子原型的 _ENV upvalue。

- [Lua 官方 luac.c 原理](https://www.lua.org/source/5.4/luac.c.html)
- [Debian Lua 5.4 luac 文档](https://manpages.debian.org/trixie/lua5.4/luac5.4.1.en.html)

**新路线**：提取/解压原始 main.blua → 原始 bytecode + 独立空手 Hook.lua 以 luac5.4 合并 → 放入 Trinity LayeredFS。

不用完整反编译或重新生成 30,829 个函数的源代码。注意 luac 仍会在内存中重新读取/保存函数原型树，不是简单把两段文件直接拼起来。

## 2. 第一步：提取真正的解压后 Lua 字节码

必须获得与 Violet 4.0.0 匹配的 arc/data.trpfd + arc/data.trpfs。原项目工具 tools/extract_trpak.py 只提取底层 pack；不要把未解压的 trpak 当成主脚本。

可用 Trinity File Explorer 导出对应的 Lua 文件（需要受支持的 Oodle 解压环境）；也可使用 pokeldn 的开源命令（在 **pokeldn 仓库**执行）：

    python tools/switch/trpfs_read.py \
      --romfs-dir /path/to/Violet_4.0.0_RomFS \
      --image /path/to/decompressed_4.0.0_main.bin \
      --extract script/lua/bin/release/main/main.blua \
      --out-dir /path/to/extracted

其 Oodle 入口 0xCC8750 来源于公开的 **Scarlet 4.0.0** 文档；用于 Violet 前需核实该 NSO 偏移和 ELF 版本正确。若解压失败，不能静默沿用错误地址。

解压后的 main.blua 标准文件头应以以下字节开头：

    1B 4C 75 61 54 00 19 93 0D 0A 1A 0A 04 08 08 ...

其中 1B Lua 54 指示 Lua 5.4，接下来的字节还包含 ABI/整数/浮点格式信息。检查：

    xxd -l 32 ./main.blua
    luac5.4 -p ./main.blua

不能对压缩数据、trpak 包或 UTF-8 反编译文本直接进行字节码合并。

## 3. 第二步：官方 luac 直接合并原版 + 空手 Hook

在 Ogre_Oustin 仓库：

    # WSL Ubuntu 常规安装
    sudo apt update
    sudo apt install lua5.4

    # 推荐调用新增的防误操作构建助手
    python3 tools/build_emptyhand_blua.py \
      /path/to/extracted/script/lua/bin/release/main/main.blua \
      build/main_patched.blua

助手会验证 Lua 5.4 签名、4/8/8 ABI 尺寸、关键方法哈希、Patch 身份，分别检查原脚本/Hook，通过官方编译器合并，再检查合并的字节码并计算输入/输出 SHA256。拒绝直接覆盖原版输入。

等价的官方命令是：

    luac5.4 -p main.blua
    luac5.4 -p patches/lua/ogre_oustin_emptyhand.lua
    luac5.4 -o main_patched.blua main.blua patches/lua/ogre_oustin_emptyhand.lua
    luac5.4 -p main_patched.blua

**必须把 main.blua 放在第一个输入，Hook 放在第二个。** 旧工具 tools/patch_main_lua.py 仅用于 UTF-8 明文 Lua；不要用它来追加到二进制主脚本尾部。

### 3.1 在标准 Lua 5.4 本地模拟中已证明什么

2026-10-24，使用 Linux liblua5.4.so.0 的 Lua 5.4.7 编译测试脚本与后置 Hook 字节码，按官方 luac.c 的 wrapper 结构构造合并后的字节码。再用 luaL_loadbufferx(binary) 加载并执行：原版函数返回 (2+x)，Hook 在原版后覆盖该函数并使返回值加 5，x=3 时结果实际为 10。_ENV 的 upvalue 处理与完整原型格式检查通过。

该证据仅证明 **标准 Lua 5.4 字节码合并可以工作**，不等于已经证明 Violet 4.0.0 完整主脚本或 Switch Lua VM 可以加载合并产物。

## 4. 第三步：Trinity 生成 Loose File + data.trpfd

Trinity 源码的 ApplyMod 会逐个提取覆盖文件，计算完整资源路径 FNV Hash，然后对 CustomFileDescriptor 调用 RemoveFile(hash)；ApplyMods 末尾将修正过的 data.trpfd 序列化。**因此并不要求将修改后的 main.blua 再压缩回原来的 Oodle trpak 文件**。此处是从 Trinity 源码推出的打包策略，需最终在游戏中验证。

[Trinity ApplyMod 源码](https://github.com/pkZukan/gftool/blob/main/TrinityModLoader/TrinityModLoaderWindow.cs) · [Mod Loader 官方 README](https://github.com/pkZukan/gftool/blob/main/TrinityModLoader/README.md)

创建 Trinity 输入目录：

    OgreEmptyHand_Trinity/
      info.toml
      script/lua/bin/release/main/main.blua  # 内容是 build/main_patched.blua

info.toml 示例：

    display_name = "Ogre Oustin Empty Hand (EXPERIMENT)"
    author_name = "969981"
    version = "0.0.1-experimental"
    description = "Offline-only experimental Lua delivery hook"

在 Trinity Mod Loader 中使用 **Add Folder Mod → Apply Mods**。生成目录应包括：

    romfs/arc/data.trpfd
    romfs/script/lua/bin/release/main/main.blua

在 Violet 4.0.0 下，安装到：

    sd:/atmosphere/contents/01008F6008C5E000/romfs/

**不可简单把自己新生成的 data.trpfd 覆盖掉其它同样有 TRPFD 的 Mod。** 应使用同一 Trinity ModPack 统一应用。若另一个 Mod 改了同一个 main.blua，则还需合并两者 Hook，不可直接让其中一个抢占文件。

加载新的 LayeredFS 文件通常需要**退出并重新进入游戏进程**。当前 PoC 的 Lua 配置默认关闭写入：enabled=false，read_only=true。只有只读链路验证通过，才应在隔离测试分支显式开启写入；不应直接用 sys-botbase 当做 Lua 控制台。

## 5. 剩余风险与验收任务

| 关键疑点 | 验证办法 | 状态 |
|---|---|---|
| 真正 Violet 4.0.0 main.blua ABI 与关键哈希 | 提取该版本资源、校验 SHA256/头/luac -p | 未验证 |
| 游戏实际 loader 接受新增的 luac wrapper | 用**默认无写入 Hook**构建/重新加载游戏验证 | 未验证 |
| Lua 原入口可能依赖 return 值（多文件 luac wrapper 会丢弃原 chunk 的返回值） | 检查原始主函数尾部控制流，以及实机初始化 | 未验证 |
| 既有 C4D2→CBA→Scene/HUD 回调是否绑定新包装函数 | 在交付点运行只读探针，核实具体调用次数 | 未验证 |
| 空手单次交付 + CLEAR + 新 Level | 完全离线真实游戏读数与视频验证 | 未验证 |

建议实施序列：

1. 提取 Violet 4.0.0 真正解压的 main.blua；运行 luac5.4 -p 验证；
2. 先 **原版主脚本重打包不加 Hook**，验证 Trinity/LayeredFS 可以无损加载；
3. 再合并默认关闭 Hook，仅验证游戏能正常进入打鬼祭；
4. 加只读交付日志确认被 Hook 的事件命中；
5. 最后才开启仅离线允许空手交付，观察一次 A → Storage +1、Carry 保持 0；
6. 测四色达标后原版 CLEAR，多关、异常与退出恢复，才将其标记为通过。

**本次成果是源码/流程研究 + 编译辅助工具；尚未发布可直接安装的成品 Mod。**
