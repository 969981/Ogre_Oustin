# V2 Stage Start Full Carry：实施任务、探针协议与实机验收

> 日期：2026-10-24。配套技术方案：[09-stage-start-full-carry-research.md](09-stage-start-full-carry-research.md)。**此文件是待实施计划，不表示已开发或已实机验证**。

## 0. 一句话验收目标

开启一个新 Level 后，屏幕要求的四种颜色树果无需打气球就已经全部在玩家的**随身携带（held）**中；玩家要自己到篮筐通过原版交付动作放下树果，**只有全部放完才正常 CLEAR**。自动适配关卡要求量、携带上限和重复切关。

禁止把 `storage` 预设满、把 `required` 改为 0、把 clear 返回值恒置 true，或者默认启用 V1 Auto Deposit/Instant Round。

## 1. 版本门槛（P0）

- 目标先限定 **Violet 4.0.0 / 离线单机**。现有 ELF 记录的完整 Build ID 为 `709bfd66115298640155fcc4979dba151c7cc79a`。
- 用用户自有的匹配 `data.trpfd + data.trpfs` 提取主 Lua TRPAK，核对 Hash 锚点和 Scene／Game／Hud 的原始方法调用体。
- 检查资源的实际内部路径，重封装时原样保持（见 `docs/05-layeredfs-trinity.md`）。
- **不上传游戏 ELF、RomFS、Lua 游戏原文**，仓库只收项目自己的 patch/代码/研究文档/测试数据。
- 记录解包工具及输入 SHA256；如果版本或锚点不符，停止写入而不是盲目加 `--force`。

## 2. 分阶段实施

| Issue | 内容 | 完成条件 |
|---|---|---|
| P0-01 | 4.0.0 原始主 Lua 校验 | `FCAFA8ED8BFD0E068`、`F96EA28F400597FA0`、`F466EB120F65C4DF8`、`F90BBC6B0190BF053` 锚点与调用链核实 |
| P0-02 | 只读 Scene/Level Probe | 进首关、下一关、重开游戏：每次捕获 round init、level、required/held/storage/cap |
| P1-01 | 配置模式隔离 | V2 下 V1 smart_balloon、auto_deposit、instant_round 均关闭，不会连锁自动交付 |
| P1-02 | 持有上限变更 PoC | 默认 30，可改到目标值；采集函数实际成功，正常交付/退出恢复；无其他隐藏限制 |
| P1-03 | 单色 1 颗预装 PoC | 无撞球可增加 held，storage 不变，UI 正确，统计副作用已知 |
| P1-04 | 单关四色预装 | 本关需要多少补多少，截图 14+4+12+11=41 这个样例能真正持有 41 |
| P1-05 | 自动切关与幂等 | 初次进入、关卡推进、重新开始，均恰好触发一次，不跨局累计 |
| P1-06 | 异常保护/回退 | 找不到实例、容量不生效、中途暂停、超时、切场景，恢复/只读记录 |
| P2-01 | 完整流程/结算 | 全部 Level 手动交付后原版 CLEAR/最终奖励、得分与原版逻辑可解释 |
| P3-01 | 双机/联机实验（**独立范围**） | 506/511/507/513 授权与同步双机一致后，再考虑多人支持 |

所有 P0/P1 工作从**只读模式**起步；不要默认开启写入或联机。

## 3. 推荐插桩方法

先用 append-only Lua monkey patch 包装：

- `C6D182891100F211D_prototype:FCAFA8ED8BFD0E068`：进入 Gameplay 时打印一条事件，并校验场景 `self[19]`；
- `C9FD31BF01E130013_prototype:FCAFA8ED8BFD0E068`：完成 HUD Reset 后递增 `resetEpoch`；
- `C6D182891100F211D_prototype:F466EB120F65C4DF8`：记录原版一颗果子到账前/后 `held`；
- 原 `F5F3E9041FE44C3C6`：在只读模式只追踪玩家手动交付，不能自动调用；
- 游戏模型 `self[3].currentLevel` 和 `self[8].playerHoldFruitsMax` 与 HUD `hud[2]`：记录而不是猜测。

**可靠 Hook 的必要条件**：不能令 wrappers 抛异常穿透原函数；禁用情况下调用原函数的时序、参数、返回值必须不变；避免多次加载导致双重包装。

### 3.1 日志结构（推荐 NDJSON，示意）

```json
{"event":"round_ready","build":"Violet-4.0.0","mode":"readonly","session":1,"epoch":3,"level":3,"active":true,"online":false,"leader":false,"required":[14,4,12,11],"held":[0,0,0,0],"storage":[0,0,0,0],"hud_cap":30,"source_cap":30}
{"event":"prefill_done","mode":"stage_full_carry","session":1,"epoch":3,"level":3,"granted":[14,4,12,11],"held":[14,4,12,11],"storage":[0,0,0,0],"hud_cap":41,"status":"pending_user_delivery"}
{"event":"manual_oblation","color":0,"held_before":14,"held_after":13,"storage_before":0,"storage_after":1,"result":"observed"}
```

字段名称仅为工具约定，不能把示例数据当实际实机日志。若只能读屏幕日志，也至少记录帧号／相对时间、是否首关、进入方法前后矩阵快照。

## 4. 自动化断言（可以用模拟状态单测）

纯算法：

```text
targetHeld[c] = max(0, required[c] - storage[c])
grant[c]      = max(0, targetHeld[c] - held[c])
wantedCap     = max(originalCap, sum(targetHeld))
```

测试用例：

| 用例 | required | held / storage (开始) | 预期 |
|---|---|---|---|
| 截图样例 | 14,4,12,11 | 0/0/0/0 | 加 41，cap≥41，storage 全 0 |
| 小关卡 | 3,2,4,1 | 全 0 | 加 10，不必扩容 |
| 有部分持有 | 14,4,12,11 | held=2,1,0,0；storage=0 | 仅再加 38 |
| 已经交付一部分 | 14,4,12,11 | held 全 0；storage=4,0,0,0 | 总目标 37，不补已交付的 4 |
| 重复 Hook | 同上一轮 | held 已达目标 | 加 0，状态不变 |
| 新一局相同 Level | 相同 required | Reset 后 held 全 0 | 应重新加，而非被旧 token 挡住 |
| cap 未扩成功 | 任意目标 >30 | 全 0 | 标记 `capacity-denied`，不得谎称成功 |
| 断网/联机 | 任意 | 任意 | 默认不执行写入 |
| 中途切关 | 任意 | 任意 | 旧 epoch 的补充任务停止 |

正式实现应将模拟测试与实机 UI/网络/分数验证区分开，禁止“算法测试通过”冒充“游戏 Mod 可用”。

## 5. 实机手工测试记录表

每个测试保存：版本与 Build ID、方法调用日志、进入/退出截图、该 Level 的 required／held／storage／cap／CurrentLevel、屏幕剩余时间、异常现象。

- [ ] 进入关卡前与后各读一次：`held[0..3]` 是否重置并且满额。
- [ ] 正常开始后**完全不碰气球**，先去某色祭台，观察按 A 一次减少 held、增加 storage。
- [ ] 一色交付完其他三色尚未交付：**不应提前 CLEAR**。
- [ ] 四色交付结束：正常显示 CLEAR 并进入下一关。
- [ ] 下一关的四色新需求不一样：按**新需求**再次补满。
- [ ] 重开相同难度 Level 1：应该重新补满。
- [ ] 样例 41，和更高关卡超过 30 的测试，不应发生数字截断、UI 损坏或误判背包满。
- [ ] 手动额外击破气球/敌人偷吃已交付树果后，是否会导致溢出或逻辑错误。
- [ ] 暂停、失败、退出、切换地图、重新入场，验证容量/脚本状态清理。
- [ ] 记录 `totalCrashBalloonCount`、`totalOblationCount` 与最终评分，验证预装与奖励的统计影响。
- [ ] 暂不测试公开联机；双机本地实验必须使用独立测试配置，遇同步差异立即停用 V2。

## 6. 发布标准

README 应用明确状态标签区分：`DESIGN`、`READONLY_TESTED`、`OFFLINE_VERIFIED`、`MULTIPLAYER_VERIFIED`。发布构建必须给出最低验证项、目标游戏 Build ID、恢复方法和已知限制。未通过 P0+P1+P2 前不要自动开启 V2 写入，不要把方案文档写成“已完成”。

## 7. Codex 实施任务提示词（复制到目标模式）

> 在 969981/Ogre_Oustin 基于 master 创建开发分支。先完整阅读 docs/01~09、patches/lua/ogre_oustin_patch.lua 与 tools/patch_main_lua.py。目标不是强制立即通关，而是每关 Gameplay 启动完成后，自动补齐四种颜色的 held，保持 storage 不变，让玩家自行正常交付。先完成 P0-01/P0-02：增加只读探针和最小自动化算法测试，不默认启用任何写入。优先验证 Scene::FCAFA8ED8BFD0E068 在 4.0.0 的原始调用链、HUD Reset、hud[2] 和 source playerHoldFruitsMax。随后分阶段实施容量调整与 Grant，旧 V1 Smart Balloon / Auto Deposit / Instant Round 与 V2 互斥；不要写 storage、不改 CLEAR flag、不绕过网络授权。每步运行测试、记录证据，更新技术文档与测试矩阵、构建说明，并提交 PR；对未拿到的 4.0.0 原始主 Lua/实机日志明确标为未验证。
