# Lua Patch design: Smart Balloon + Auto Deposit + Instant Round

This is the implementation note for `patches/lua/ogre_oustin_patch.lua`.

The design goal is to preserve the game's own game-state, UI, statistics and network transitions by intercepting high-level Lua methods instead of writing arrays or forcing completion flags.

## Patch insertion strategy

The safest current strategy is **append-only monkey patching**:

1. start from a user-extracted unmodified main Lua for the target game version;
2. verify expected 3.0.1-era hash anchors are present;
3. append the patch after the game's class/prototype definitions have been created;
4. save a new patched Lua as a separate file;
5. put that patched resource back into its original TRPFS virtual path and let Trinity rebuild the LayeredFS output.

The repository tool `tools/patch_main_lua.py` performs steps 2–4. It refuses to patch by default if any of these anchors are missing:

```text
C6D182891100F211D
FCE25070892D46E56
F466EB120F65C4DF8
F5F3E9041FE44C3C6
CE506B90C88D90C92
C9FD31BF01E130013
CC07CA97E7F9D78F4
```

The patch is delimited with:

```text
-- OGRE_OUSTIN_PATCH_BEGIN
...
-- OGRE_OUSTIN_PATCH_END
```

so accidental double-patching can be rejected.

## Exact high-level patch points

### 1. `C6D...::FCE25070892D46E56` — OnCrashBalloon

Original semantic signature:

```lua
FCE25070892D46E56(self, crash_event, color)
```

The patch saves the original function, calls it first, then optionally performs Smart Balloon fill.

Why this function is the correct trigger:

- it is reached by a real balloon collision;
- the original network 506/511 logic still executes first;
- the second argument is the color already resolved by the game;
- the patch does not need to scan actors or infer color from world data.

### 2. `C6D...::F466EB120F65C4DF8` — local/received GetKinomi

Original semantic signature:

```lua
F466EB120F65C4DF8(self, color)
```

Internally this forwards to the game model's `FCE250...`, which increments `totalCrashBalloonCount`, attempts to add one carried fruit and updates UI state.

The patch wraps this function for **Auto Deposit**. It first lets the original grant occur, then performs a normal `TryOblation` attempt.

### 3. `C6D...::F5F3E9041FE44C3C6` — TryOblation

Semantic signature:

```lua
F5F3E9041FE44C3C6(self, color, remote_flag, source_station)
```

The patch does not replace this method. It calls the saved original as:

```lua
Original.TryOblation(self, color, false, nil)
```

The `false, nil` form is taken from a normal call site in the recovered public script rather than invented.

## Smart Balloon

The useful amount for a popped color is:

```text
missing = max(0, required - storage - held)
room    = max(0, holdCap - totalHeld)
extra   = min(missing, room)
```

The patch then calls the saved original local grant helper `extra` times.

Important behavior:

- the legitimate balloon operation runs before the patch;
- no raw matrix write occurs;
- the game's high-level fruit statistics/UI path is reused;
- auto-fill is only enabled where this console is offline or session leader;
- a non-leader client is not allowed to fabricate additional local fruit.

That last restriction is intentional. A remote client's normal grant is authority-issued through packet 511. Future multiplayer work should reuse the original 511 sender with an explicit target station rather than cheating the client's local matrix.

## Auto Deposit

The wrapper around `F466...` runs after a normal local/received fruit grant.

For one color:

```text
need  = max(0, required - storage)
count = min(held, need)
```

It then calls the saved original `TryOblation` path.

For non-leader network clients, the default patch only attempts one delivery for each received fruit event. This avoids an unvalidated burst of 507 messages in a single Lua tick.

For offline/leader logic, the patch may drain multiple useful carried fruit while checking that Carry actually decreases after each call. If no progress is observed, the loop stops rather than spinning.

## Instant Round

`OGRE_OUSTIN_PATCH.CompleteCurrentRound()` is the manual high-level entry point.

It can also be enabled automatically through:

```lua
OGRE_OUSTIN_PATCH.config.instant_round_on_first_balloon = true
```

Algorithm:

```text
for color = 0..3:
    while storage[color] < required[color]:
        if held[color] == 0:
            grant only useful fruit, respecting hold capacity
        call original TryOblation(color, false, nil)
        verify Carry decreased
```

The routine never calls or patches `F58184E938BDF8E80` to return true. The last normal storage increment is expected to make the original all-color check succeed and drive the original next-level/result sequence.

## Runtime configuration

Once the patch is loaded, the global table is:

```lua
OGRE_OUSTIN_PATCH
```

Available flags:

```lua
OGRE_OUSTIN_PATCH.config.smart_balloon = true
OGRE_OUSTIN_PATCH.config.auto_deposit = true
OGRE_OUSTIN_PATCH.config.instant_round_on_first_balloon = false
OGRE_OUSTIN_PATCH.config.allow_online_host = true
```

Useful manual call when a script console/debug injection path exists:

```lua
local ok, reason = OGRE_OUSTIN_PATCH.CompleteCurrentRound()
```

## Why append instead of rewriting original functions in-place

In-place replacement of the generated Haxe-Lua body is fragile because local variable numbering and formatting can change across dumps/decompilers even when behavior is the same.

A monkey patch only needs stable global class/prototype hash names and function hashes. The patcher therefore verifies those names and leaves the original generated body untouched.

## Known limitations

1. Public symbol semantics are derived from a 3.0.1-era script dump. 4.0.0 hash stability must be verified against a real extracted script.
2. The exact 4.0.0 TRPFS virtual pathname of the game main Lua is not available from the ELF alone and must be read from a 4.0.0 `data.trpfd` / RomFS.
3. Remote Smart Balloon for another station is intentionally not implemented yet; the correct path should reuse the original 511 sender.
4. Multiplayer packet timing still needs a two-console validation pass before enabling aggressive drain/fill loops for non-leader clients.
5. If the game's Lua loader snapshots prototype methods before this patch is appended, an earlier insertion point will be needed. The runtime validation document includes a test for this.
