# 打鬼祭 V2：新 Level 开始即满额持有树果（保留手动交付）

> 2026-10-24 | 目标：《宝可梦 紫》4.0.0 | 状态：**静态链路研究 + 设计，尚未完成 4.0.0 主 Lua/实机验证**  
> 相关已有资料：[01 ELF](01-elf-4.0.0.md) · [02 状态模型](02-lua-state-and-functions.md) · [03 联机](03-network-protocol.md) · [04 现有 Patch](04-lua-patch-design.md) · [08 TRPFD](08-trpfd-4.0.0-main-lua.md)

## 1. 用户目标与边界

**准确需求**：每次开启新的 Level（首关及下一关），在进入可操作的 Gameplay 后，四种颜色的**随身携带（held）**树果直接补齐至本关需要数量；此时祭台/篮筐中的**已交付（storage）**仍保持原版数值（通常为 0），玩家仍需主动回到对应颜色的祭台按原版方式交付，从而触发原版 CLEAR 和进入下一关。

与已有功能的区别：

| 方案 | 何时触发 | 修改什么 | 是否仍需手动交付 |
|---|---|---|---|
| 旧 Smart Balloon | 击破一个气球后 | 对应颜色 held 补充 | 可选（旧版 Auto Deposit 会自动交付） |
| 旧 Instant Round | 击破首个气球后 | 自动补充 + 自动尝试交付 | **否** |
| **本提案 Stage Start Full Carry** | **每次开始新 Level** | **四种颜色 held 一次补齐** | **是** |
| 直接填 storage / 强制 CLEAR | 任意时刻 | 完成状态 | 否，不符合要求 |

**禁止混淆**：界面左上/上方的四种颜色目标量不能认作已经收集的量；运行时行 1 是 required，行 0 才是 held，行 2 才是 storage。

### 1.1 截图样例

用户提供的 Level 截图上方依次为 **14 / 4 / 12 / 11**，合计 **41**；右侧祭台显示 0/0/0/0。截图不等同于实时内存观测，数字对应关系还应由 V2 只读探针核实。基于 UI 初步推定：

```text
required[4] = {14,4,12,11}
held[4]     = {0,0,0,0}      # 进入关卡时的假设值，须实机读取
storage[4]  = {0,0,0,0}

期望补充后的：
held[4]     = {14,4,12,11}
storage[4]  = {0,0,0,0}
总携带 41；游戏原始携带上限通常为 30。
```

普通玩法的 30 个携带上限已见 [Serebii](https://www.serebii.net/scarletviolet/ogreoustin.shtml)、[Bulbapedia](https://bulbapedia.bulbagarden.net/wiki/Ogre_Oustin%27)。**关卡需求为随机分色且可能受玩家人数影响，绝不可把截图数字写死**；须读取本关实际 required。

## 2. 基础证据与可信度

| 证据 | 结论 | 可信度 / 适用范围 |
|---|---|---|
| 仓库 [01-elf-4.0.0](01-elf-4.0.0.md) | 4.0.0 Violet ELF 为 AArch64 PIE，GNU Build ID `709bfd66115298640155fcc4979dba151c7cc79a`；已定位 native Ojama 行为，但不是高层果子数组 | **已有仓库静态分析结果**；本次未重新打开二进制 |
| [SV-Script-RE](https://github.com/Martmists-GH/SV-Script-RE) `decompiled/C6D182891100F211D.lua` | 场景管理器函数及切关流程可还原 | **已核对公开 3.0.1 时代 Lua**，4.0.0 必须复核 |
| 同项目 `decompiled/CA2A924A55DC1CE8A.lua` | 游戏模型 `currentLevel`、HUD Reset、关卡进度和统计 | 同上 |
| 同项目 `decompiled/C9FD31BF01E130013.lua` 与 `CC07CA97E7F9D78F4.lua` | held/required/storage 的 3×4 模型；容量 `hud[2]` | 同上 |
| 仓库 [08-trpfd-4.0.0-main-lua](08-trpfd-4.0.0-main-lua.md) | 4.0.0 主要 Lua pack 为 `arc/scriptluabinreleasemainmain.blua.trpak` | 已解析用户提供的 4.0.0 TRPFD；**pack 名不是 inner resource 路径** |
| 本次两张视频截图 | 上方 14/4/12/11，下方祭台皆 0 | UI 观察；不是内存或运行时证明 |

**严禁将已有 ELF 中的 Ojama native 偏移冒充为新 Level Hook 地址。** 新 Level 的准确语义目前来自脚本层；如果以后要编成 exlaunch，必须在 4.0.0 的实际 Lua→native 桥接调用中再次验证对应 PC/LR、参数和地址。

## 3. 精确的入口：Gameplay Start 而非 Balloon Crash

### 3.1 推荐 Hook

`C6D182891100F211D`（场景管理器）：

```text
SceneProto:FCAFA8ED8BFD0E068(A1_2)
```

公开反编译体的语义顺序：

1. `self[14]:FCAFA8ED8BFD0E068(A1_2, callback)`：游戏模型更新关卡计数，并让 HUD 根据本关需求执行重置；
2. `self[4]:FCAFA8ED8BFD0E068()`、`self[6]:FCAFA8ED8BFD0E068()`：使相关控制器进入 Gameplay；
3. `self[19] = true`：标记激活状态；
4. 派发 `SET_STATE_ONIBALLOON_GAMEPLAY`。

因此推荐 **wrap 此函数并先执行 original，在函数返回后再进行 V2 补齐**。不要在场景对象创建时、Reset 之前或旧版 `OnCrashBalloon` 上实现新关卡预装。

相关重要链路：

```text
首次开局／过渡至下一关
  Scene::FCAFA8ED8BFD0E068
    └─ GameModel::FCAFA8ED8BFD0E068
         ├─ statistics.currentLevel += 1
         └─ HudModel::FCAFA8ED8BFD0E068(requirements, callback)
              └─ FruitsViewSupporter::F96EA28F400597FA0(requirements)
                   ├─ row 1 required = requirements[0..3]
                   ├─ row 2 storage = 0
                   └─ row 0 held    = 0
  → Scene::FCAFA8ED8BFD0E068 原函数返回
  → [V2 StageFullCarry] 快照+容量处理+逐色 grant
  → 玩家自行到篮筐交付
  → 原版 TryOblation / 清关 / 下一关
```

**注**：上图为由公开脚本推导的业务调用链。实际 4.0.0 异步回调顺序、客户端路径仍需插桩核实。

### 3.2 关键类 / 函数

| 类与标识 | 静态推定含义 | V2 用途 |
|---|---|---|
| Scene `C6D182891100F211D` | 打鬼祭场景控制器 | `self[14]` 持有游戏模型；`self[19]` Active |
| Scene `FCAFA8ED8BFD0E068` | 切入 Gameplay | **V2 新关卡触发点** |
| Game `CA2A924A55DC1CE8A` | 游戏规则与分数 | `self[1]` 为 HUD，`self[3].currentLevel` |
| Hud `C9FD31BF01E130013` | 树果 HUD 模型 | `hud[2]` 为携带上限，`hud:FA3DF24554485BE54(row,c)` 读计数 |
| Supporter `CC07CA97E7F9D78F4` | 3 行 × 4 色实际数据 | Reset 为 `F96EA28F400597FA0` |
| Scene `F466EB120F65C4DF8(c)` | 正常接收本地树果 | 复用既有 Grant 路径（需检查 UI/分数副作用） |
| Scene `F5F3E9041FE44C3C6(c,false,nil)` | 交付 | **V2 不自动调用，玩家自行触发** |
| Game `F58184E938BDF8E80()` | 四色全部达标检查 | **V2 不覆写** |

## 4. 30 个携带上限：必须明确方案

公开代码显示 `Scene::FF34481551C0A54B9()` 初始化时把 `self[8].playerHoldFruitsMax` 传给 `GameModel::F90BBC6B0190BF053`，进而到 `HudModel::F90BBC6B0190BF053(requirements, holdCap, timeLimit)`；Hud 将 `holdCap` 存在 `hud[2]`。

`HudModel::FCE25070892D46E56(c)` 的采集检查包含 `totalHeld >= hud[2]`，超过时不会入账。图中需求总 41，单纯循环 41 次只能成功至上限 30。

### A（推荐功能目标）：随身袋临时扩容到本关目标合计

```text
desiredHeld[c] = max(0, required[c] - storage[c])
targetTotal    = sum(desiredHeld[0..3])
effectiveCap   = max(originalCap, targetTotal + safetyMargin)
```

在补充前把游戏中的**有效携带容量**提高到至少 `targetTotal`；最小 PoC 可在本关重置完成后调整 `hud[2]` 并验证 `IsFull/Grant`；正式设计应在参数传入与所有相关检查点之间保持一致，并且在退出场景后恢复原值。不应未经测试把常驻全局参数强制改成 999。

- 优点：真正做到开启关卡时获得全部树果，之后**只需手动送货**。
- 风险：其他 HUD、动画或 native 检查仍假定最大 30；某些 UI 容量显示可能异常，特殊敌人造成丢果、同步包大小、分数逻辑都需验证。
- 多人难度/最终关卡需求可能达到约 200（见 [Bulbapedia 人数/关卡表](https://bulbapedia.bulbagarden.net/wiki/Ogre_Oustin%27)），优先根据运行时要求计算而非永久改成 200/255/999。

### B（降级兼容）：保留上限 30，分批自动补充

每次关卡开始先按原上限装满；送至篮筐后，当 Carry 下降再补足剩余需求，不动原版容量。缺点是它**不满足“只在开始时一次装齐”**，且会在送货时动态增加随身树果，需避免误触或重复投递。仅作为方案 A UI/逻辑不兼容时的回退模式。

### C（不建议）：直接改 required / storage

减少 required、把 storage 直接设满或改 clear 返回值，都可能跳过实际手动交付、造成统计/UI/通信不一致；与目标矛盾，故不实现。

## 5. V2 预装算法（设计伪代码，非已验证可运行补丁）

**先关掉旧功能**：新模式下 `smart_balloon=false`、`auto_deposit=false`、`instant_round_on_first_balloon=false`；否则在填 held 时，旧 Auto Deposit 可能把它立刻交付，偏离需求。

```lua
-- PSEUDOCODE: 要结合现有 OGRE_OUSTIN_PATCH 集成，不能直接当生产补丁运行
local OriginalGameplay = SceneProto.FCAFA8ED8BFD0E068

SceneProto.FCAFA8ED8BFD0E068 = function(self, ...)
    local result = OriginalGameplay(self, ...)  -- 先让关卡初始化和 HUD Reset 完成
    if not cfg.enabled or not cfg.stage_full_carry then return result end
    if cfg.offline_only and IsNetworkActive() then return result end

    local game, hud = self[14], self[14] and self[14][1]
    if not game or not hud or not self[19] then return result end
    local round = game[3].currentLevel
    local token = GetResetEpochOrSessionRoundToken(self, round)
    if token == lastCompletedToken or busy then return result end

    local needed, held, stored = {}, {}, {}
    for c = 0, 3 do
        needed[c] = hud:FA3DF24554485BE54(1, c)
        held[c]   = hud:FA3DF24554485BE54(0, c)
        stored[c] = hud:FA3DF24554485BE54(2, c)
    end

    local target = 0
    for c = 0, 3 do
        target = target + math.max(0, needed[c] - stored[c])
    end

    if cfg.capacity_mode == "extend" then
        -- 只是示意：验证其它容量检查点后再决定最终入口
        hud[2] = math.max(hud[2], target)
    end

    busy = true
    local ok = true
    for c = 0, 3 do
        local delta = math.max(0, needed[c] - stored[c] - held[c])
        for i = 1, delta do
            local before = hud:FA3DF24554485BE54(0, c)
            -- 使用现有 P.GrantLocalFruit / saved original，
            -- 禁止经过旧 auto_deposit wrapper
            GrantFruitViaOriginalHighLevelPath(self, c)
            local after = hud:FA3DF24554485BE54(0, c)
            if after ~= before + 1 then ok = false; break end
        end
        if not ok then break end
    end
    busy = false
    if ok then lastCompletedToken = token end
    -- 对未完成状态记录日志；不能静默标记全关满额
    return result
end
```

设计要求：

1. **四色分别按差值计算**：`delta[c] = max(0, required[c] - storage[c] - held[c])`，不预设颜色具体数量、不要超额补充。
2. **幂等且按局重置**：不能只用 `currentLevel` 去重；重新开一局 Level 1 也要触发。优先在 HudModel 每次 Reset 时递增 `resetEpoch`，用 `session + resetEpoch` 作唯一键。
3. **不能破坏原函数的多返回值**：上面单 `result` 是简化写法；正式 Lua Wrapper 应保留原函数 varargs 与全部返回值。
4. **实际加果成功以 held 的前后变化为准**，不能只数“调用了几次”。明确记录达到 cap、对象 nil、关卡切换、超时、中断等失败。
5. **不自动调用 TryOblation**、不改 storage、clearFlag、关卡数，不模拟全部气球实体。
6. **避免一帧 200 次 UI 更新卡顿**：高关卡可试每帧 8～16 次，期间检测同一轮次 token；但分帧依赖真实 4.0.0 游戏调度器接口，不能使用普通 Lua 任意 sleep。
7. **统计副作用**：原高层 Grant 路径会递增 `totalCrashBalloonCount`，可能导致最终分数按伪造气球数增加。建议增加 `statistics_mode = original|preserve_real_crashes` 配置；后者可能需要捕获/恢复统计快照并验证所有回调，**不得声称已实现无副作用**。
8. **退场恢复**：如改写了容量或实例配置，离开打鬼祭或开始新局需恢复原版值，并防止在旧实例释放后继续执行。
9. **失败保留原版行为**：任何探针异常都只能停止预装，不能让原交付/过关被阻断。

## 6. 离线与多人不能直接等价

仓库 [03 网络协议](03-network-protocol.md) 已梳理：

```text
506  CrashBalloon 原始事件
511  GetKinomi 授权发果
507  Oblation 正常交付
513  StorageNum 祭台数量同步
```

- **单机**：优先验证 V2 全额预装 + 玩家手动交付 + 正常 CLEAR。
- **本地多人**：需要实测 Leader 与非 Leader 的授予权、容量同步、每个玩家是否独立持有 held。
- **互联网**：默认关闭 V2。Leader 本地私改 held 不等于其它成员持有相同树果；非 Leader 禁止凭本地内存伪造授权。若以后支持，必须逐站复用 511 授权发果和 507/513 原版同步，分析宿主/客户端容量一致性以及收包限流。两机一致性未验证前不得声称联机可用。
- **不要用对 storage 的直接写入绕过 507/513**；这会让屏幕、联机参与者以及 clear 判断不同步。

## 7. 和现有 Patch 的集成建议

当前 `patches/lua/ogre_oustin_patch.lua` 是实验性 V1，默认 `smart_balloon=true, auto_deposit=true`。新功能应以显式模式切换集成到同一全局 `OGRE_OUSTIN_PATCH`，不要同时替换互相冲突的函数。

建议新增配置：

```lua
P.config.mode = "stage_full_carry"    -- "original"|"smart_balloon"|"stage_full_carry"|"instant_round"
P.config.stage_full_carry = true
P.config.capacity_mode = "extend"     -- "extend"|"batch_fallback"
P.config.stage_trigger = "gameplay_start"
P.config.offline_only = true
P.config.preserve_original_clear = true
P.config.auto_deposit = false
P.config.log_readonly = true
```

建议 V2 先交付一个独立 **只读 Probe**：包装 Gameplay、Hud Reset 和 GetKinomi，打印 `scene instance / level / resetEpoch / active / required[] / held[] / storage[] / hud[2] / networkActive / leader`，保持原返回值、不写任何果子/参数。

验证通过后再按“容量扩展 → 一色预装 → 四色预装 → 每关自动触发 → 退出恢复”逐层开放。在正式 patch 里应复用 V1 缓存的 `Original.GrantLocalFruit`（可以通过受控接口暴露），避免旧版 Auto Deposit 包装器的重入。

### 静态验证所需 4.0.0 资源

该仓库目前已有 4.0.0 `data.trpfd` 的静态结果，但**没有**以本次会话重新提取 4.0.0 主 Lua。后续需与其版本匹配的 `arc/data.trpfs`，提取 `arc/scriptluabinreleasemainmain.blua.trpak`，检查其中 `FCAFA8ED8BFD0E068` / `F96EA28F400597FA0` / `F466EB120F65C4DF8` / `playerHoldFruitsMax` 锚点是否确实存在，不能仅靠 Build ID 的 16 位前缀断言版本相同。详见 [05](05-layeredfs-trinity.md)、[08](08-trpfd-4.0.0-main-lua.md)。

## 8. 推荐执行次序

1. 新增 read-only scene/level probe；实机确认每关 Hook 命中次数、Reset 顺序和截图的 required 数值。
2. 验证单机 `hud[2]` 与 `self[8].playerHoldFruitsMax` 实际生效范围；不预装时游戏行为必须完全相同。
3. 做 **1 种颜色只加 1 颗** PoC，验证 held/UI/分数副作用。
4. 自动预装一关（截图 41 颗）并手动完成全部 4 色交付，不自动点交付。
5. 连过多 Level，验证每关再次触发、退出后恢复，以及结束难度后的奖励结算。
6. 如需联机，再独立开发权威链路版本并用双机验证；不要将离线 PoC 直接宣传为联机支持。

## 9. 可交付判定

- 每关原版 required 保持不变；
- 每关开始玩家 Carry：`held[c] == required[c] - storage[c]`（正常非负前提下）；
- 祭台 storage 仍为 0，直到玩家按原版按钮交付；
- 截图样例总 41 颗不会被原本的 30 上限截断；
- 不击破任何气球，仅手动交付也能使四色逐一达标并进入 CLEAR；
- 相邻 Level 重新填满，且不因为切场景或同关重试重复叠加；
- 游戏不掉帧/异常卡住，退场容量恢复，结算奖励正常；
- 联机模式未验证前拒绝写入；
- 同一份 4.0.0 主 Lua 的锚点对照、实机日志和至少一次完整 Hard 模式通关视频齐备，才标为 validated。

---

### 公共源码原始路径

- [SV-Script-RE / Scene Manager](https://github.com/Martmists-GH/SV-Script-RE/blob/master/decompiled/C6D182891100F211D.lua)
- [SV-Script-RE / Game Model](https://github.com/Martmists-GH/SV-Script-RE/blob/master/decompiled/CA2A924A55DC1CE8A.lua)
- [SV-Script-RE / HUD Model](https://github.com/Martmists-GH/SV-Script-RE/blob/master/decompiled/C9FD31BF01E130013.lua)
- [SV-Script-RE / Fruit Supporter](https://github.com/Martmists-GH/SV-Script-RE/blob/master/decompiled/CC07CA97E7F9D78F4.lua)
- [Serebii — Ogre Oustin](https://www.serebii.net/scarletviolet/ogreoustin.shtml)
- [Bulbapedia — Ogre Oustin](https://bulbapedia.bulbagarden.net/wiki/Ogre_Oustin%27)
