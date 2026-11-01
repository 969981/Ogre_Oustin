# 《宝可梦 朱／紫》4.0.0 太晶团体战：1× HP + 不开盾（实验版）

**实际交付类型：Trinity Mod Loader 导入包，非可直接复制的 IPS。**
**当前验证：静态 Lua 字节码结构校验、本机 Lua 5.4 可加载；游戏内开盾、击倒、胜利与奖励未验证。**

## 目标功能

- `hpCoef=100`：RaidPoint 的 HP 系数是百分数，100 对应 1× 原始宝可梦 HP（不是伤害倍率）。
- `powerChargeTrigerHp=0`：把 Boss 剩余 HP 的开盾触发百分比降至 0。
- `powerChargeTrigerTime=0`：把剩余时间开盾触发百分比降至 0。
- 不修改常规伤害公式、不在每次命中时篡改 HP、不强制改变结算和奖励。
- 0 阈值是否被脚本/Native 当作永不触发、是否有特殊 Boss 脚本强制开盾，要实际测试。

### 版本/验证状态

| 游戏 | Title ID | 本包使用的 Lua 来源 | 状态 |
|---|---|---|---|
| 朱 4.0.0 | `0100A3D008C5C000` | 原始 `main.blua` SHA `c1a4f4e2625912cf0b739a642a79ba3357df0557a544b92da22a6cb139de2815` | 静态构建完成；游戏运行未验证 |
| 紫 4.0.0 | `01008F6008C5E000` | 使用**相同的朱版脚本**生成兼容候选 | 紫版主脚本字节一致性**未核实**；有不兼容/闪退风险 |

两者都不能声称“已通过实机”；紫版尤其需要从对应 4.0.0 RomFS 提取原生 `main.blua` 比对 SHA。

## Trinity 导入（朱/紫分别）

1. **备份游戏存档**，退出游戏；使用匹配该游戏 4.0.0 的原始 RomFS 作为 Trinity Mod Loader 的基底。
2. 打开 Trinity Mod Loader，选择 **Add ZIP Mod**，导入对应 `...TRINITY_*.zip`。
3. 在同一个 ModPack 中 **Apply Mods**。确认输出至少有这两个文件：
   - `romfs/arc/data.trpfd`
   - `romfs/script/lua/bin/release/main/main.blua`
4. **朱**：把整个输出 `romfs` 放到 `sd:/atmosphere/contents/0100A3D008C5C000/romfs/`。
   **紫**：放到 `sd:/atmosphere/contents/01008F6008C5E000/romfs/`。
5. 模拟器：使用相同 Trinity 输出 `romfs`，放进其对应游戏的 LayeredFS Mod 文件夹；不要把 ZIP 直接当成 IPS。
6. 关闭游戏进程后重新启动，仅做**离线测试**：进入太晶团体战，确认开盾、HP、胜利／捕获／奖励是否正常。

**注意：不能直接把 ZIP 解压到 `atmosphere/contents/`。** 单独 Loose `main.blua` 通常还需要 Trinity 修正对应的 `arc/data.trpfd`，以覆盖打包的原始资源。与其他修改同一个 `main.blua` 或 `data.trpfd` 的 Mod 须合并，不能简单覆盖。

## 复现构建

源码文件：`source/build_raid_profile_experiment.py`、`source/build_sv400_raid_1xhp_noshield.py`。

```bash
python source/build_sv400_raid_1xhp_noshield.py --original /path/to/main.blua --game scarlet --out dist
python source/build_sv400_raid_1xhp_noshield.py --original /path/to/main.blua --game violet --violet-candidate --out dist
```

输入脚本必须与已知朱版 4.0.0 SHA256 完全一致，防止误补其他版本。构建脚本使用 `root/7833` (`CE6.Get`) 中 3 处带原始 opcode 断言的 SETFIELD 跳转，不覆盖其它原型。

## 完成/未完成验证

- **通过**：源文件 SHA 检查；原字节码指令守卫；3 处参数注入；修改后 Lua 5.4 Chunk 解析到 EOF；liblua5.4 `luaL_loadfilex` 返回成功；构建包结构检查。
- **未验证**：Trinity 实际 Apply Mods 输出、Eden/Ryujinx 或实机实际加载、屏蔽全部护盾事件、胜利/奖励正常性、紫版版本兼容性、多机联机同步。

**不要用于公共网络匹配。** 本项目的范围是本地离线研究；正常奖励不会因为保留原生结算代码就自动得到保证。