# 4.0.0 runtime validation plan

The Lua patch is intentionally marked experimental until it is checked against a real Pokémon SV 4.0.0 script resource and at least one runtime session.

## Phase 1 — static script identity

Extract the 4.0.0 main Lua through Trinity File Explorer and run:

```bash
python tools/patch_main_lua.py extracted/main.lua build/main.lua
```

Expected result:

```text
anchor check: OK
```

If any hash anchor is missing, stop and compare the 4.0.0 function bodies before forcing the patch.

Minimum anchors:

```text
C6D182891100F211D
FCE25070892D46E56
F466EB120F65C4DF8
F5F3E9041FE44C3C6
CE506B90C88D90C92
C9FD31BF01E130013
CC07CA97E7F9D78F4
```

## Phase 2 — patch load test

Start with all automation disabled by changing the appended patch configuration to:

```lua
smart_balloon = false
auto_deposit = false
instant_round_on_first_balloon = false
```

Boot the game and enter/leave Ogre Oustin'. This verifies that the patch is being parsed and that prototype replacement itself does not break scene creation.

If a Lua/debug console is available, check:

```lua
OGRE_OUSTIN_PATCH ~= nil
```

and confirm the scene instance becomes non-nil while the minigame is active:

```lua
C6D182891100F211D.S032897EBFF9CC1F2
```

## Phase 3 — state-model confirmation

During a fresh round, inspect all four colors through:

```lua
local s = C6D182891100F211D.S032897EBFF9CC1F2
local h = s[14][1]

for c = 0, 3 do
  local held = h:FA3DF24554485BE54(0, c)
  local need = h:FA3DF24554485BE54(1, c)
  local stored = h:FA3DF24554485BE54(2, c)
end
```

Expected:

- row 0 begins at 0;
- row 1 matches visible current-round requirements;
- row 2 begins at 0;
- `h[2]` matches the effective carry limit;
- popping one fruit-producing balloon increments the corresponding row-0 value by one.

## Phase 4 — Auto Deposit only

Enable only:

```lua
auto_deposit = true
```

Keep Smart Balloon and Instant Round disabled.

Expected behavior after one legitimate fruit grant:

1. Carry for that color increases through original GetKinomi handling;
2. patch calls original `TryOblation`;
3. Carry decreases normally;
4. Storage increases through original delivery logic;
5. UI updates normally;
6. no forced clear occurs.

Record whether the fruit is delivered immediately from any map position or whether the original method still applies proximity/table gating. If there is a proximity requirement, the automation must move to a lower business-layer function or intentionally bypass that specific gate while preserving network messages.

## Phase 5 — Smart Balloon only

Enable only:

```lua
smart_balloon = true
```

Offline test:

1. record `held`, `required`, `storage`, total held and hold cap;
2. pop one balloon of a known color;
3. verify final held amount becomes exactly `required - storage` for that color unless carry capacity is reached;
4. verify other colors are unchanged;
5. verify the total crash-balloon statistic changes consistently with each high-level grant call.

Edge cases:

- target color already satisfied;
- only one fruit missing;
- carry bag nearly full with other colors;
- carry bag full;
- requirement becomes satisfied mid-fill.

## Phase 6 — Instant Round offline/leader

Set:

```lua
instant_round_on_first_balloon = true
```

Expected after the first legitimate balloon event:

- the current round fills/deposits through original high-level methods;
- each color reaches normal Storage requirement;
- the original `F58184E938BDF8E80` check becomes true;
- the game transitions through the normal next-level or result flow;
- result UI is not skipped or replaced by a raw flag write.

Repeat for early, middle and final difficulty levels.

## Phase 7 — multiplayer two-console validation

Use two consoles/instances and log host/client values after every action.

### Host pops balloon

Confirm:

```text
host original OnCrashBalloon
-> local grant and/or authority flow
-> Smart Balloon extra local grants only on host
-> any generated storage changes are reflected on client through normal synchronization
```

### Client pops balloon

The current patch must **not** locally Smart Fill on the non-leader client.

Confirm normal flow:

```text
client 506
-> host/leader resolve
-> host 511
-> client F466 grant
```

With Auto Deposit enabled, confirm the client sends one normal delivery attempt after a received fruit rather than producing a local-only storage mutation.

### Packet/runtime trace targets

If using a native hook/debugger, capture PC/LR/X0-X7 around the native network send boundary for these script calls:

- CrashBalloon send (506)
- `F55A0610336E1F729` GetKinomi send (511)
- Oblation send (507)
- StorageNum send (513)

Store runtime addresses as:

```text
main+offset = PC - main_base
```

This is the clean path to a future exlaunch/native implementation if desired.

## Phase 8 — remote Smart Balloon research

Do not implement by writing the remote player's state.

Instead identify the payload used by the original 511 sender:

```text
targetStation
color
other/result field(s)
```

Then test a host-issued normal 511 to a selected remote station and verify:

- only target station receives the fruit;
- its own `F466...` runs;
- statistics/UI remain normal;
- no duplicate grant is created on host.

Only after this passes should remote auto-fill be added.

## Pass criteria for calling the patch “4.0.0 validated”

All of the following should be true:

- anchor check succeeds without `--force`;
- patch loads without startup/minigame errors;
- 3×4 row semantics match runtime values;
- Smart Balloon never overfills a color or carry capacity;
- Auto Deposit uses normal UI/stat/network flow;
- Instant Round reaches the next-level/result state without a direct clear write;
- non-leader client does not fabricate local fruit;
- two-console storage state remains synchronized after repeated tests.
