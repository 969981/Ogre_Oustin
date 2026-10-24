# 14 — Library 主脚本 main.blua 实测分析（2026-10-24）

> 样本来自用户在 ChatGPT Library 中持有的 `main.blua`。**仅公开 SHA、文件头、结构计数、函数标识与测试结论，不上传或再发布原版游戏二进制。**
>
> 对应前序研究：[11 空手交付](11-direct-emptyhand-oblation-research.md)、[13 Lua 5.4 合并路线](13-v400-blua-bytecode-merge-trinity.md)。

## 1. 实测文件身份

| 字段 | 实测 |
|---|---|
| 文件名 | `main.blua` |
| 文件长度 | **12,912,264 字节** |
| SHA-256 | `c1a4f4e2625912cf0b739a642a79ba3357df0557a544b92da22a6cb139de2815` |
| 文件头 | `1B 4C 75 61 54 00 19 93 0D 0A 1A 0A 04 08 08 78 56 00 00 00 00 00 00 00 00 00 00 00 28 77 40` |
| 格式 | 未压缩的、可直接读取的 **Lua 5.4 Binary Chunk** |
| ABI | 4 字节 Instruction、8 字节 lua_Integer、8 字节 lua_Number |
| Lua C API 加载 | 本机 `liblua5.4.so.0`（5.4.7）`luaL_loadfilex(path,"b")` **返回 0（成功）**，栈顶为函数类型，未执行游戏脚本 |

**关键版本限制：这个 SHA-256 与 pokeldn 公开的 `Scarlet 4.0.0` `main.blua` 完全一致**。出处是 [pokeldn / docs/sv_union_circle.md](https://github.com/decryptu/pokeldn/blob/main/docs/sv_union_circle.md)。其不能独立证明该文件也正好是 `Violet 4.0.0` 的脚本；未来制作紫版 Mod 必须从紫版匹配的 RomFS 提取或与紫版资源比对 SHA。

本仓库旧有的 `Violet4.0.0.elf` 与本样本对应的游戏版本标签**不能因脚本格式相同或某些哈希相同而自动关联**。

## 2. 自制只读 Lua 5.4 原型解析：100% 解析至 EOF

依据 Lua 官方 [ldump.c](https://www.lua.org/source/5.4/ldump.c.html) / [lundump.c](https://www.lua.org/source/5.4/lundump.c.html) 的标准序列化布局，逐项只读解析 Varint、Function、Code、Constants、Upvalues、Children、Debug：

| 结构 | 数值 |
|---|---:|
| 根函数 `sizecode` | **429,034** 条指令 |
| 根函数 `sizep` | **30,829** 个直属子原型 |
| 全部递归函数原型（含根） | **37,743** |
| 最大嵌套深度（根深度 0） | **8** |
| 根函数 `sizek` | **45,106** 个常量 |
| 根函数 `sizeupvalues` | **1** |
| 解析结束偏移 | **12,912,264 / 12,912,264**（精确到 EOF） |

这不仅验证了头部签名，还完整检验了文件内的结构序列化。公开 pokeldn 的“30,829 prototypes”指的是**根函数直属子原型**，而非所有递归嵌套函数的总和；两个统计并不矛盾。

根函数最后一条 32-bit Instruction 是 `0x0101A2C6`，解码 opcode=70，Lua 5.4 的 `OP_RETURN`，B 字段为 1，表示**返回 0 个值**。因此官方 luac 多文件合并的“忽略前一个 Chunk 返回值”在此样本上不大可能损失有意义的原始返回值；此项仅分析入口指令，不代替 Switch 运行时验证。

## 3. 与打鬼祭业务链的实证关系

下面的字节串在**已完整解析的原生 Lua 字节码**中出现：

| 哈希/文本 | 字节匹配次数 | 静态研究语义 |
|---|---:|---|
| `C6D182891100F211D` | 55 | 打鬼祭 Scene |
| `C9FD31BF01E130013` | 5 | HUD |
| `CBA116AC4A909C38C` | 3 | 篮筐交付 Controller |
| `F5F3E9041FE44C3C6` | 4 | TryOblation/交付路径 |
| `FD9E6D41945878085` | 6 | CanOblation/交付条件 |
| `CC07CA97E7F9D78F4` | 4 | Fruit 数据支持类 |
| `FCAFA8ED8BFD0E068` | 11 | Gameplay 切关相关 |
| `SET_STATE_ONIBALLOON_GAMEPLAY` | 2 | 进入打鬼祭 Gameplay 状态 |

这批值不是纯 grep 得到的“不知道是否存在于结构中的随机字符串”：在**成功解析后的 Function Constants** 中可定位到：

- 根原型的函数常量表包含 `C6D...` / `CBA...` / `C9FD...` / `TryOblation` / `CanOblation` 等锚点；
- 子原型编号 `0.16902` 含 `FD9E6D41945878085` 字符串常量，含 108 条指令与一个内层子函数；
- 子原型 `0.16916` 包含 `SET_STATE_ONIBALLOON_GAMEPLAY`；
- 子原型 `0.16963` 包含 `C9FD31BF01E130013`。

**限制**：编译字节码存在对应方法名称，不等于已经基于 Violet 4.0.0 完成每个函数的 ABI、调用顺序与动态 Hook 命中证明。严格说 0.16902 是一个含相关常量的函数原型，而不是在未经反汇编时断言它就是 `IsCanOblation` 定义。

## 4. 标准 Lua 5.4 的真实加载和重导出

已用运行库的 C API 对这个**实际 12.9 MB 样本**（不是自己制造的短 Lua 例子）执行：

1. `luaL_loadfilex(L, path, "b")`：状态 0，Lua 栈顶类型 function。没有执行游戏主脚本，因此没有依赖 Switch 提供的 API。
2. `lua_dump(L, writer, nullptr, 0)`：可成功再次输出字节码，大小 **12,959,198 字节**，与原始的 **12,912,264 字节**并非字节相同。
3. 再导出 SHA-256：`a5cb2e42c102eb8ea7e3c9dab20a64a40ff594626811529ae0f934f5904bd245`。

**已精确归因，并完成全原型结构比较**（新增验证）：

- 将原始 `main.blua` 与 `lua_dump` 重导出文件逐个解析为 **37,743 个同路径 Proto**；
- **0** 个 Proto 的机器指令、常量值与类型、Upvalue 绑定描述（instack/idx/kind）、参数、栈设置、子 Proto 数量发生变化；
- 调试区域唯一差异为 **29,656** 个 Proto 的 `upvalue_names` 列表：原始文件以长度 0 省略，Lua 5.4.7 重导出在对应有 Upvalue 的函数上补写若干个 `nil` 名称占位；
- 这类空名称占位恰好增加 **46,934** 字节，**精确等于**两个文件的体积差 `12,959,198 - 12,912,264 = 46,934`；没有其它结构差异。

**结论：该真实文件在 Lua 5.4.7 的 load → dump 过程中，37,743 个原型的可执行字段语义保持一致，差异仅为 Upvalue 调试名称的规范化**。这为正式 `luac5.4` 合并提供强于只验证文件头的证据。但这仍**不是**对最终新增 wrapper chunk / Trinity/Switch 的实机兼容证明。

## 5. 直接关系到空手交付 Mod 的技术结论

### 已解决

- 文件无需再经过 Oodle 解压，也不是 Trinity pack；可以直接喂给标准 Lua 5.4 加载器。
- `main.blua` 主体整体格式正确。
- Ogre Oustin 核心函数/类哈希实际存在于 4.0.0 的 Scarlet 样本中。
- 不需要将所有 30,829 个直属函数原型反编译成源码后才可能追加 Hook。
- 入口 Chunk 最终 RETURN 0 个值，降低了官方 `luac` 多输入包装影响原版返回值的风险。

### 尚未通过

- **这份 main.blua 的游戏归属已被其精确 SHA 指向 Scarlet 4.0.0**；要对 Violet 4.0.0 负责，仍需要匹配 Violet 的脚本或验证两者完全一致。
- 本会话运行环境有 `liblua5.4` 但没有官方 `luac5.4` CLI，因而尚未对**此 12.9 MB 实际原版样本**执行 `luac5.4 -o 原版+Hook` 的合并产物测试。以前只对模拟小 chunk 进行合并原理测试。
- Trinity 生成的 loose-file `data.trpfd` + `main.blua` 尚未在 Switch 实机加载。
- 尚未证明空手进入篮筐时，原版的 C4D2 → CBA → Scene → HUD 交付链在该实机上准确命中。

## 6. 推荐下一步

1. **优先取得 Violet 4.0.0 的匹配主 Lua**，与本 Scarlet 文件比较 SHA，并对关键方法原型作有控制的函数级比较。若只是想验证《朱》4.0.0，此现有文件已可作为 Scarlet 研究基线。
2. 在安装 `lua5.4` 编译工具的本机 Windows WSL 中运行 `tools/build_emptyhand_blua.py`，确认真实样本合并后能 `luac5.4 -p`。
3. Trinity 输出严格保持 `script/lua/bin/release/main/main.blua` 原路径，同时新 `data.trpfd` 与其他同类 Mod 的冲突需合并处理。
4. 首次进入游戏应只用 `enabled=false / read_only=true` 的 Hook，避免直接写入交付状态；稳定后仅在**离线**单次测试“空手交付一次 → 原版 Storage +1”。

原始 `main.blua` 是游戏资产，不上传仓库；只提交分析结论和由项目开发者自己写的 Hook、构建辅助工具。
