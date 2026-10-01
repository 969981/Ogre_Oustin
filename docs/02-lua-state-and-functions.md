# Lua state model and function map

Primary public reference used to recover semantics: `Martmists-GH/SV-Script-RE` (3.0.1-era at the time of its README).

The names below are hash-based generated identifiers. Friendly names are semantic labels inferred from assertions, call sites and behavior; the hash identifiers are the important part for patching.

## Top-level scene manager

`C6D182891100F211D` ≈ `OniballoonAppliSceneManager`.

Important instance slots:

- `self[14]` → `CA2A924A55DC1CE8A`, core Ogre Oustin game model/coordinator.
- `self[19]` → active/in-round style gate used by storage synchronization/round logic.
- `self[8]` → game-base parameters including difficulty-related values.

Important methods:

| hash | semantic role |
|---|---|
| `FCE25070892D46E56(crashEvent, color)` | high-level `OnCrashBalloon` entry |
| `F466EB120F65C4DF8(color)` | local/received `GetKinomi` grant helper |
| `F5F3E9041FE44C3C6(color, remoteFlag, sourceStation)` | `TryOblation` / delivery path |
| `S00019E6412AEEDCF(...)` | static receive crash-balloon handler |
| `S2F658F4F9A2C0446(...)` | static receive GetKinomi handler |
| `SF8DF85A80A4D3875(...)` | static receive Oblation handler |
| `S103E7501A3CE388E(...)` | static receive StorageNum handler |

A normal non-network caller was found invoking `F5F3E9041FE44C3C6(false, nil)`, which is why the experimental patch uses `TryOblation(self, color, false, nil)` for local automation rather than inventing argument values.

## Game model

`CA2A924A55DC1CE8A` is the high-level game model/coordinator.

Important slots:

- `self[1]` → `C9FD31BF01E130013` HUD/game fruit model.
- `self[3]` → statistics object containing at least:
  - `totalCrashBalloonCount`
  - `totalOblationCount`
  - `currentLevel`
  - `totalElapsedTime`

Important methods:

### `FCE25070892D46E56(color, ui)` — add one carried fruit

Behavior:

1. increments `totalCrashBalloonCount`;
2. calls the HUD model fruit-add function;
3. if the add succeeds, updates UI with color count / total held / full state / can-oblate state.

This is why calling the scene manager's `F466EB...` is preferable to `held[color]++`: the higher-level statistics and UI path remain intact.

### `FDA889B72B2C16758(color, ui)` — oblation / carried fruit decrement

Behavior:

1. increments `totalOblationCount`;
2. decrements carried fruit through the HUD model;
3. updates UI/total-held state.

### `FC6917C3380AB1540(color, ui, extra)` — add one storage fruit

Behavior:

1. calls HUD-model `OnAddStorage`;
2. updates the visible storage count and need count;
3. checks whether this color has just reached the required number and emits the color-complete callback.

### `F58184E938BDF8E80()` — round clear check

Loops `color = 0..3` and delegates to the HUD model's `IsClearColor`. It returns true only when all four colors are clear.

The patch deliberately never replaces this result with a forced true value.

## HUD / fruit model

`C9FD31BF01E130013` ≈ `OniballoonHudModel`.

Important slots:

- `self[3]` → `CC07CA97E7F9D78F4` concrete fruit-state supporter.
- `self[2]` → carry/hold capacity. Its `Init` stores the second argument here. In normal data this corresponds to the configured fruit-hold maximum.

Important methods:

| hash | meaning |
|---|---|
| `FA3DF24554485BE54(row, color)` | get one fruit matrix value |
| `F7A6F9EAA9E4B39B9(row)` | get one full row |
| `F214C1CBB9948C146()` | total held across colors |
| `F891CDEA8CE6093D3()` | carry full check (`totalHeld >= self[2]`) |
| `F2206A10AD8E18ED0(color)` | `held + storage == required` |
| `FCE25070892D46E56(color)` | add one held fruit if capacity allows |
| `FDA889B72B2C16758(color)` | decrement one held fruit |
| `F8F5EC534C6723DA0(color)` | increment one storage fruit |
| `F852BCD89E06A2905(color)` | clear-color check |

## Concrete 3×4 fruit state

`CC07CA97E7F9D78F4` ≈ `FruitsViewSupporter`.

The constructor creates a matrix of 3 rows × 4 colors and initializes all entries to zero.

`Reset(requirements)` proves the row semantics:

- row `0` → carried/held fruit, reset to 0;
- row `1` → required/current-need fruit, copied from the round requirement array;
- row `2` → storage/table fruit, reset to 0.

Therefore, for a color `c`:

```text
held[c]     = matrix[0][c]
required[c] = matrix[1][c]
storage[c]  = matrix[2][c]
```

Confirmed primitive operations:

```text
OnCrashBalloon(c): held[c]++
OnOblation(c):     if held[c] > 0 then held[c]--
OnAddStorage(c):   storage[c]++
IsClearColor(c):   required[c] <= storage[c]
IsJustNeed...:     required[c] == storage[c]
TotalHeld():       sum(held[0..3])
```

## Smart-fill arithmetic

The patch computes only the amount still useful to the current round:

```text
missing = max(0, required[color] - storage[color] - held[color])
room    = max(0, holdCap - totalHeld)
extra   = min(missing, room)
```

This prevents over-collecting a color and respects the game's normal carry capacity unless the parameter itself is separately modified.

## Parameter-side observations

Public pkNX schema/data work shows Ogre Oustin game-base parameters including `TimeLimit`, `PlayerHoldFruitsMax`, `DifficultyLevelMax`, `BaseFruitsNeedNum`, `AdjustMemberNums`, `BalloonAutoRepopTime`, `CountupAnimeSeconds`, and `SeOblationResetSeconds`.

A public extracted data example has historically shown values such as hold max 30 and time limit 120. Treat these as data-layer reference values, not as values recovered from the uploaded 4.0.0 ELF. Runtime or 4.0.0 RomFS validation is still required before claiming byte-for-byte identity.
