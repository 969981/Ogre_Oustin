# 12 — 空手交付实现选型和独立 Lua PoC

2026-10-24，目标 Pokémon Violet 4.0.0。本次交付的是**开源 Lua Hook + 本地模拟测试**，**尚未完成 4.0.0 主脚本封装、实机验证或可直接安装的 LayeredFS/IPS**。先阅读 [11 — 原版交付链逆向](11-direct-emptyhand-oblation-research.md)。

**2026-10-24 更新：** 经 [pokeldn 的 4.0.0 逆向文档](https://decryptu.github.io/pokeldn/sv_union_circle.html) 与 Lua 官方 `luac` 源码核实，4.0.0 main.blua 是 **Lua 5.4 bytecode**，内层路径 `script/lua/bin/release/main/main.blua`。官方 luac5.4 支持**直接合并原始字节码 + 我们的独立 Hook Lua**，而 Trinity 可以把新 main.blua 作为 loose 资源叠加。此前“必须解编译整份脚本才能修改”的前提已取消。参见 [13 最新构建流程](13-v400-blua-bytecode-merge-trinity.md) 和 [build_emptyhand_blua.py](../tools/build_emptyhand_blua.py)。下文对二进制不可直接追加纯文本的提醒仍然成立。

## 1. 该选 Lua、sys-botbase 还是 IPS？

| 方案 | 本功能能做什么 | 结论 |
|---|---|---|
| **Lua Hook + Trinity/LayeredFS** | 精确包装原版交付流程，只在合法本地交付时放行当前颜色的空手资格 | **优先验证**，已有 PoC |
| sys-botbase | 远程读写内存、控制器操作，可协助定位对象/运行时日志 | 不是 Lua Hook 引擎，不能把 Lua 哈希直接当内存地址 |
| Atmosphère cheat 文本 | 找到可靠 native 指令地址后做可开关的执行期补丁 | 暂无已验证地址 |
| IPS/IPS32 | 修改 NSO 静态 AArch64 指令 | 还需要 ELF/IDA 找到真实 Native 条件分支；Lua 哈希不是 IPS offset |
| exlaunch/subsdk9 | Native Hook、Mailbox、实时配置、Tesla | 适合未来热切换，但开发/验证工作更多 |

上游参考：[sys-botbase](https://github.com/olliz0r/sys-botbase)、[Atmosphère NSO IPS](https://github.com/Atmosphere-NX/Atmosphere/blob/master/docs/components/modules/loader.md)、[Atmosphère Cheats](https://github.com/Atmosphere-NX/Atmosphere/blob/master/docs/features/cheats.md)、[Trinity/gftool](https://github.com/pkZukan/gftool)、[SV-Script-RE](https://github.com/Martmists-GH/SV-Script-RE)。

## 2. 源码和测试

- [独立空手交付 Lua PoC](../patches/lua/ogre_oustin_emptyhand.lua)
- [模拟 Scene/HUD/Station 测试](../tests/test_emptyhand.lua)
- [Python + liblua 测试运行器](../tests/run_emptyhand_tests.py)
- [原版逻辑和函数明细](11-direct-emptyhand-oblation-research.md)

独立 PoC 与旧版 Smart Balloon / Auto Deposit 互斥。配置默认：enabled=false、read_only=true、offline_only=true、trace=false。

### 关键逻辑

1. 包装 CBA116AC4A909C38C 的 F5F3E9041FE44C3C6（本地交付控制器），只在非远程、正常参数的调用期记录同一 Scene + Color。
2. 包装 C6D182891100F211D 的 F5F3E9041FE44C3C6（TryOblation），仅在当前关卡 Gameplay Active、网络被识别为离线、当前颜色未达标、held=0 且匹配上层交付调用时允许一次实验操作。
3. 包装 C9FD31BF01E130013 的 FD9E6D41945878085（IsCanOblation）。**仅在这一次同步 TryOblation 的作用域内**返回 true，其他调用仍用原版逻辑。
4. 原版 TryOblation 负责增 Storage、视觉反馈、交付统计与清关。PoC 不直接修改果子数量矩阵、不改 required、不修改携带上限、不置 CLEAR、不主动造网络消息。
5. 使用 pcall + 全返回值转发，异常或正常退出均恢复 Guard。

**限制**：来自 CBA 控制器的调用不能证明玩家一定处于祭台物理范围；必须在 4.0.0 实机确认 C4D2B0FE0245F3E65 的交互触发调用链。NetworkClass 返回 false 也尚不能证明所有本地无线模式均关闭，实验只能在人工确认的完全离线模式做。

### 本地模拟测试

    python3 tests/run_emptyhand_tests.py

当前模拟测试通过：默认关闭、read-only、仅原交付控制器调用、单次空手增 Storage、返回值保留、远程/联网/未知网络不放行、满额不再增加、原函数异常恢复、重新加载不重复 Hook，以及下一关再交付。

这些是**本地模拟验证**，不等于真正游戏运行。

## 3. 从 Lua 源代码变成可安装 Mod 的关键障碍

仓库 [08 — 4.0.0 主 Lua Pack](08-trpfd-4.0.0-main-lua.md) 已确定 TRPFD 名称为：

    arc/scriptluabinreleasemainmain.blua.trpak

这个字符串是 Pack 名称，不一定是其内部唯一资源的路径。用户须有对应 4.0.0 的 data.trpfd + data.trpfs，并通过 Trinity File Explorer / tools/extract_trpak.py 得到内层脚本资源。

**必须首先识别脚本是 UTF-8 文本还是压缩/编译后的 .blua 字节码**。现有 tools/patch_main_lua.py 只会检查文本 hash 并追加 Lua 代码，**不是编译器，不能直接把补丁附在 .blua 二进制尾部并替换游戏资源**。若为字节码，必须确认游戏 Lua VM/编译格式，完成合法的兼容回编译和对应的资源重封装。

若确实提取出兼容的 UTF-8 Lua 文本源，现有工具可以用于**静态补丁生成阶段**：

    python3 tools/patch_main_lua.py extracted/main.lua build/main.emptyhand.lua --patch patches/lua/ogre_oustin_emptyhand.lua

这个命令生成的只是补丁文本，不是可以在 Switch 安装的 Mod。不能为了通过 hash 校验而直接使用 --force。

之后须用 Trinity Mod Loader 的 Add Folder Mod / Apply Mods，保留**原始内层路径**生成 LayeredFS，装入：

    sd:/atmosphere/contents/01008F6008C5E000/romfs/...

重新启动游戏才会载入新的 RomFS 数据。源文件不能直接复制到 SD 卡当作已完成的补丁。

## 4. 如果要运行中切换开关

已经证明存在兼容 Lua VM 调用/console 后，才可通过 Lua 配置表启停当前 Hook。**仅安装 sys-botbase 并不能执行 Lua 语句**。如果必须没有 Lua VM 入口且不想重启游戏，后续应研究 ELF/IDA Native hook、exlaunch/subsdk9 + Mailbox，或者在定位稳定的 AArch64 修改点后生成 Atmosphère Cheat 文本。IPS 更适合固定指令补丁，通常需要重新进入游戏以载入被修改的 NSO。

## 5. 现场验收

在离线模式中：某关红色需 14、held=0、storage=0。直接到红色交付点触发原版交付一次，预期 Storage 从 0 变 1、Carry 仍为 0，交付特效/统计正常。直到红色 14 后停止增加；其他颜色未满不应 CLEAR；四色均达标才通过原版判断切至下一 Level。必须记录调用次数和日志，测重新开局/退出/恢复，还必须测试真实 4.0.0 的主 Lua 是否具有相同哈希、同步行为和对象布局。

**Codex 后续任务**：先根据用户自己的 4.0.0 RomFS 验证脚本资源及编译/解编译闭环，在只读模式确认交付链，再做默认关闭的离线单次交付试验。未经实机验证，不发布标称 Switch 可直接安装的包，也不宣称在线多人可用。
