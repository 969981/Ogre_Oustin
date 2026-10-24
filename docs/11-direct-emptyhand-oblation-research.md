# 11 — 打鬼祭直接交付：空手交果（Direct Oblation / No Harvest）研究

> 2026-10-24 | Pokémon Violet 4.0.0 目标 | **代码静态研究，未验证 4.0.0 实机；不是已可使用的补丁。**
>
> 推荐优先级：**Direct Empty-Hand Oblation（空手交付）** > Just-in-Time 单颗补果 > [09 自动满额携带](09-stage-start-full-carry-research.md)。用户体验为“开启关卡 → 直接到相应颜色的篮筐旁 → 按原版 A 交付 → 四种颜色完成后正常 CLEAR”，**不打气球，不必扩容 30 个携带上限**。

## 0. 目标和操作方式

- 只对当前 Level 存在的颜色需求生效；`required[0..3]` 原封不动，`storage[0..3]` 从 0 开始。
- 玩家移动到**对应颜色的正常交付点**并按原版 A 键；不远程修改祭台，也不替代进入交付点/按键动作。
- 即使 `held[color] == 0`，正常交付业务路径仍允许该次交付；它每次将 `storage[color]` 增 1，保留正常计分、音效、UI、最终 CLEAR 及切关流程。是否能连续、持续按键全额交付，由原版交付速率/场景时序及实机验证决定。
- 假设截图需求 14、4、12、11，总计 41。该模式不需要一次携带 41，也不需要任何真实或虚拟树果。
- 用户按 A 的操作有公开玩法资料佐证：[Nintendo Life](https://www.nintendolife.com/guides/pokemon-scarlet-and-violet-ogre-oustin-tips-how-to-win-mochi-all-rewards)、[Adventure Guide](https://bulbapedia.bulbagarden.net/wiki/Adventure_Rules)。**本文未声称一按 A 自动完成整色**，这是后续可选扩展。

## 1. 新发现：原版“可否交付”的唯一显式前置检查

静态证据来自 [Martmists-GH/SV-Script-RE](https://github.com/Martmists-GH/SV-Script-RE) 的 **3.0.1 时代**公开解编译文件，以下全部哈希名尚需与用户提取的 4.0.0 原版主 Lua 逐一核对。

### 1.1 真正的交付点事件入口

在 `decompiled/C4D2B0FE0245F3E65.lua` 中：

```text
C4D2B0FE0245F3E65::FDA98E87C57449F00(eventActors)
  scene = C6D182891100F211D.S0B3F69C4549A0284()
  if scene == nil or not scene:FDD69EA99F11D731F() then return end
  if eventActors.length == 0 then return end
  actor = eventActors[0].owner
  controller = lookup actor component by actor identity
  controller:F5F3E9041FE44C3C6(false, nil)
```

这里的 `Scene::FDD69EA99F11D731F()` 仅返回 `self[19]`（Gameplay 激活位）。**在这段事件入口里没有查询 Carry 是否大于 0**；未携带树果仍可能触发正常交付入口（需实机看交互 UI 是否有另一层限制）。

由 `decompiled/CBA116AC4A909C38C.lua`：

```text
CBA116AC4A909C38C::F5F3E9041FE44C3C6(isRemote, station)
  -> self[14]:F5F3E9041FE44C3C6(self[8] /* color */, isRemote, station)
  -> 如果返回非 nil，显示 BERRY_CONTINUE_COUNT、交付音效/粒子与颜色完成音效
```

在 `CBA::F7C68FEDB79AB6396` 中可见交互回调注册 `OnRegistTriggerFunction`。这让 **保留原版碰撞/交付动作，只绕过果子资格检查** 有了具体入口，不必自己推测玩家位置或直接写场景状态。

### 1.2 第一层：真正拦截空手交付的是 IsCanOblation

`decompiled/C6D182891100F211D.lua`：

```text
Scene::F5F3E9041FE44C3C6(color, remoteFlag, station)
  -> GameModel::FD9E6D41945878085(color)
  -> if false and not remoteFlag:
       UIManager::F386F6DC04963E7F5(color)   # 不可交付反馈
       return nil
  -> Offline:
       GameModel::FDA889B72B2C16758(color, UI)
       callback:
          GameModel::FC6917C3380AB1540(color, UI, other)
          check F58184E938BDF8E80() -> next stage/result
  -> Online: 507 / 513 authority/sync branch
```

`GameModel::FD9E6D41945878085` 转发 `HudModel::FD9E6D41945878085`：

```text
C9FD31BF01E130013::FD9E6D41945878085(color)
    return held[color] > 0
```

故而空手尝试正常返回 `nil`，不会累计 storage；如果只在一次原版交付调用作用域中让此判断返回 true，那么在**离线模式**中，余下原版流程有机会正常执行。

### 1.3 第二层：扣果在 0 时原本就是 no-op（关键）

`decompiled/CC07CA97E7F9D78F4.lua`：

```text
CC07CA97E7F9D78F4::FDA889B72B2C16758(color)
    if held[color] == 0 then return end
    held[color] -= 1
```

而 `GameModel::FDA889B72B2C16758(color, ui)` 仍会：

- 累加 `totalOblationCount`；
- 调用 Hud 的上述扣果函数（0 时保持不变，不会减为 -1）；
- 更新原版 UI 的持有数量与总持有数。

其后，正常交付回调 `GameModel::FC6917C3380AB1540` 会调用原版 `Hud::F8F5EC534C6723DA0` 让 `storage[color]` **加一**，UI 也走原版更新回调，然后 `F58184E938BDF8E80` 做四色清关检查。

**这不是宣称“游戏自动赠送树果”，而是让既有的交付业务链在没有 Carry 时仍可执行**；在 3.0.1 静态函数体层面这个方向成立，在 Violet 4.0.0 的实际 UI、触发器、能力判定与游戏稳定性仍未验证。

## 2. 推荐模式：只在有效本地交付动作里临时放行

不建议永久 `Hud::IsCanOblation = function() return true end`，因为 Scene 的另一条 `FA0FB7B5C3B7ACE47` 也会查询该 predicate 来显示/隐藏交付 UI，且全局改变会影响其它调用。

建议包装 **Scene::F5F3E9041FE44C3C6** 并在原版执行期间设置 **Scoped Guard**，同时包装 HUD `FD9E6D41945878085`：

```text
正常走近篮筐 + A 键
  -> 原版 C4D2 collider/interaction callback
  -> 原版 CBA Controller(color)
  -> [本地离线/Gameplay/本色未满/零 Carry] Scene::TryOblation 包装器
       -> 只对当前 hud 实例、当前 color、当前同步调用启用 allowEmpty
       -> 调用 original Scene::TryOblation(color, false, nil)
           -> 原版 CanOblation 检查临时通过
           -> 原版 Model/Supporter 的扣 Carry 是 0 时 no-op
           -> 原版 Storage += 1
           -> 原版统计/动画/消息/clear check
       -> 即使异常也移除 Scoped Guard
  -> 原版 CBA 控制器的果子交付视觉反馈
```

### 2.1 伪代码（不可直接安装，避免误报可用）

```lua
-- Design only. 实际需要检验 4.0.0 Lua API 和原方法调用；
-- 不与旧 V1 Auto Deposit 同时启用。
local OriginalCan = HudProto.FD9E6D41945878085
local OriginalTry = SceneProto.F5F3E9041FE44C3C6
local guard = nil

HudProto.FD9E6D41945878085 = function(hud, color)
    if guard and guard.hud == hud and guard.color == color then
        return true
    end
    return OriginalCan(hud, color)
end

SceneProto.F5F3E9041FE44C3C6 = function(scene, color, isRemote, station)
    if not cfg.enabled or cfg.mode ~= "direct_oblation" then
        return OriginalTry(scene, color, isRemote, station)
    end
    if isRemote or IsNetworkActive() or not scene[19] or guard ~= nil then
        return OriginalTry(scene, color, isRemote, station)
    end

    if type(color) ~= "number" or color < 0 or color > 3 then
        return OriginalTry(scene, color, isRemote, station)
    end
    local game = scene[14]
    local hud = game and game[1]
    if not hud then return OriginalTry(scene, color, isRemote, station) end

    local held = hud:FA3DF24554485BE54(0, color)
    local required = hud:FA3DF24554485BE54(1, color)
    local stored = hud:FA3DF24554485BE54(2, color)

    if held > 0 or stored >= required then
        return OriginalTry(scene, color, isRemote, station)
    end

    guard = {hud=hud, color=color}
    -- 必须把 original 的完整返回值/异常安全透传，并在任何路径恢复 guard。
    -- 此处用抽象方法表示具体 Lua 多返回值/保护调用机制。
    local ok, returns = ProtectedInvokeWithFullReturns(OriginalTry, scene, color, isRemote, station)
    guard = nil
    if not ok then raise(returns) end
    return UnpackAll(returns)
end
```

核心是 **predicate 只在业务处理中的同步调用被放行**，而不是直接 `storage = required`，也不是通过无限循环对空果子使用旧 V1 auto-deposit。

若 4.0.0 运行时发现事件在到达 Scene::TryOblation 之前被 UI/动作层阻拦，再单独对 `CBA` / `C4D2` 的**原版交付触发**做最窄范围探针；不要改原版场景坐标或全域放行。

## 3. 单次交付与整色快速交付

### V1 建议：一次 A = 正常交付 1 次

这一档最保守：每次靠近对应祭台按 A，`storage[color]` 就 +1，直到该颜色达标。以截图举例，原目标依旧为红 14、绿 4、蓝 12、灰 11。无需打气球，也不需装满 41 个，**是否每次都能触发以 4.0.0 实机为准**。

### V2 可选：在该颜色交付点一次触发即可完成对应颜色

待 V1 通过后，可以用“同色逐次调用原版 TryOblation，按正常节奏分帧执行”的模式：`left=max(0,required[color]-storage[color])`。必须：

1. 首次触发是原版交付点/输入事件，不是地图任意位置；
2. 绑定当前 `scene/roundResetEpoch/color`，离开交付范围、中途变关、已满或失败必须停；
3. 每次只处理 **一笔**正常交付，等待游戏当前帧/动画/同步状态，并重新读取 `storage`；
4. 不要一次性把 N 次 TryOblation 递归塞进同一个 A 键回调。最后一次可能会使 `self[19]=false` 并换关，继续调用旧实例危险；
5. 若客户端/主机授权关系变化，直接停用；
6. 虽然没有 Carry 扣减，原版 `totalOblationCount` 仍会上涨并影响评分；应记录，而不擅自清零。

其中 “离开范围检测”需要在 CBA/C4D2 交互生命周期里验证可靠标志。此前用 `scene[19]` 只代表玩法激活，**不是**站在交付点附近。

## 4. 网络限制 / 不应贸然用于联机

现有 [03-network-protocol](03-network-protocol.md) 指出了：

- packet **507**：正常交付；
- packet **513**：祭台计数同步；
- packet **511**：权威发果。

在联网情况下，Script `TryOblation` 是发送/接收分支，不是离线的立即 `storage += 1`。若没有 Carry，服务端/Leader 或同步环节可能拒绝、回滚或导致队友不同步。因此研究版强制：`offline_only=true`，不得在外服/联机环境默认开启；多人研究应另起验证任务而非顺手取消检查。

## 5. 对比结论（推荐用户选择）

| 维度 | 旧 09 满额携带 | 交付前临时 +1 | **空手直接交付** |
|---|---|---|---|
| 新 Level 开始时 | 补四种 held | 什么都不做 | **什么都不做** |
| Carry 上限 | 可能需要 41/更多 | 无需扩容 | **无需扩容** |
| 采集计数 | 原 Grant 可能增加 `totalCrashBalloonCount` | 增加 | **不增加** |
| 交付计数 | 正常累加 | 正常累加 | **正常累加** |
| 祭台更新 | 正常交付 | 正常交付 | **正常交付** |
| 玩家体验 | 带所有果子四处交 | 走到篮筐交 | **走到篮筐按 A 交** |
| 额外 Hook | Level Start / capacity / grant | Input / grant | **Scene Try + Scoped CanOblation** |
| 当前验证 | 未实机 | 未实机 | **静态链条比较强；4.0.0 未实机** |

## 6. 开发与实机验证任务

- **D0 静态身份**：提取 `Violet 4.0.0` 的 `main.blua`，检验五个类 `C6D...`、`C9FD...`、`CA2A...`、`CC07...`、`C4D2...` 和六个方法锚点是否保持一致。
- **D1 只读探针**：站在篮筐且 `held=0`，按 A，确认 `C4D2::FDA98...` → `CBA::F5F3...` → `Scene::F5F3...` 真实命中；录 `color, held, required, storage, sceneActive`。
- **D2 空手资格门验证**：单机离线仅允许一次当前颜色、当前 Scene 的 CanOblation；按 A 后捕获 Can 检查、0 Carry 扣果、Storage +1 的原版函数命中及返回值。
- **D3 退出/异常**：测试撤销 Scoped Guard；其他 UI 的 `IsCanOblation` 调用不被污染。
- **D4 手动全关**：颜色只增加一次/按键；未达到四种 required 不提前 CLEAR；满额按原版下一关；回到新 Level 继续有效。
- **D5 正常统计**：真实气球数 0，统计 `totalCrashBalloonCount` 不意外增加，`totalOblationCount` 会因虚拟交付增长，确认结算与奖励。
- **D6 整色可选**：在完整验证 D0-D5 后，才加入有速率限制、离开范围即停的“同色自动连续交付”。
- **D7 联机**：不在 V1 范围。两台机器做权威协议研究后再评估，绝不声称已经通过。

### 验收场景

```text
关卡 N，截图需求 14/4/12/11
held        = 0/0/0/0
storage     = 0/0/0/0

直接来到红色祭台，按 A 一次：
held        = 0/0/0/0          # 不从零减成负数
storage     = 1/0/0/0          # 原业务链 +1
totalOblationCount = +1
totalCrashBalloonCount = 不变
原版正常交付动作及 UI 可见

继续按 A 将四种颜色依次交至所需：
storage     = 14/4/12/11
-> 原版四色 IsClear 为 true
-> 原版 CLEAR / 下一 Level

切关后 storage 重置为新关要求的起点；
再次直接空手到篮筐，仍能正常交付。
```

以上是**预计观察值**，不是游戏 4.0.0 已采集的实机测试结果。

## 7. 下一阶段 Codex 目标模式指令

在 969981/Ogre_Oustin 仓库阅读 docs/01~11、现有 patches/lua/ogre_oustin_patch.lua 以及开源 Martmists-GH/SV-Script-RE 中 C6D182891100F211D、C4D2B0FE0245F3E65、CBA116AC4A909C38C、CA2A924A55DC1CE8A、C9FD31BF01E130013、CC07CA97E7F9D78F4。**改为优先研究 Direct Empty-Hand Oblation**：玩家无果子到对应祭台按正常 A 键也可以完成一颗交付，调用原版 TryOblation/Storage/UI/CLEAR；保留原版四种颜色需求和过关过程，不进行采果、不扩容、不自动强制 CLEAR。首先实现 OFF/READONLY 两种无写入配置，验证 Collider→Controller→Scene→Model→Storage 的 4.0.0 真实链路，再做默认关闭的离线只放行 PoC，必要时用 Scene Try 同步作用域的 HUD CanOblation Guard；完成测试和日志后单独提交 PR。旧 Auto Deposit / Smart Balloon / Instant Round 与该模式互斥。严禁上传游戏脚本原文和用户 ELF、不要声称未经实机验证的联机支持。
