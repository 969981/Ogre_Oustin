# Ogre Oustin network protocol / authority flow

This document records the script-layer packet dispatch observed in `CE6DE953128959840` (`OniballoonNetMediator`) and related network-manager methods.

## Packet IDs relevant to the fruit loop

| ID | semantic role | receiver path |
|---:|---|---|
| 506 | CrashBalloon event | parse crash object → authority-side crash resolution |
| 507 | Oblation / berry delivery | parse oblation payload → `OnRecieveOblation` |
| 511 | GetKinomi / fruit grant result | parse grant payload → `OnReceiveGetKinomi` |
| 513 | StorageNum / storage snapshot | parse four-color storage values → `OnRecieveStorageNum` |
| 514 | OjamaHit | Ojama hit receive path |

Other IDs in the same dispatcher include 502, 503, 504, 510 and 512, but they are not required for the current Smart Balloon / Auto Deposit implementation.

## CrashBalloon → GetKinomi authority chain

The important correction from early research is that **511 is not the original balloon collision event**.

The normal online flow is closer to:

```text
Client collides with balloon
  -> OnCrashBalloon
  -> packet 506
  -> authority/leader receives 506
  -> resolve balloon and color
  -> construct GetKinomi result
  -> network-manager F55A0610336E1F729(...)
  -> packet 511
  -> target station receives 511
  -> verify target station
  -> C6D...::S2F658F4F9A2C0446
  -> C6D...::F466EB120F65C4DF8(color)
  -> GameModel::FCE25070892D46E56(color,...)
  -> held[color]++ + statistics/UI
```

The authority-side function `CE6DE953128959840.S6D8ADEB9091E95E3` handles the crash result, calls `C6D...::S00019E6412AEEDCF`, then—when the local system is the session leader and the result is valid—constructs a GetKinomi payload and sends it through `F55A0610336E1F729`.

The 511 receiver checks the destination station before applying the grant. This is why a host-only local `held[color]++` cannot substitute for a remote player's GetKinomi packet.

## Meaning for Smart Balloon

There are two distinct cases:

### Offline / local leader fruit

It is safe for the experimental patch to reuse `F466EB120F65C4DF8(color)` because this is the same high-level local fruit grant helper reached after a legitimate 511 receive.

### Remote client fruit

A host that wants to grant fruit to another station should ultimately reuse the **original 511 sender path**, not mutate its own `held` matrix and not assume another console will mirror it.

The current Lua patch intentionally implements Smart Balloon auto-fill only for offline/local-leader state. Remote Smart Balloon generation remains a runtime-validation task because target-station payload construction and 4.0.0 timing should be confirmed in a real multiplayer session.

## Oblation / delivery chain

`C6D182891100F211D::F5F3E9041FE44C3C6(color, remoteFlag, sourceStation)` is the high-level `TryOblation` path.

Its behavior includes the important pieces we do not want to reimplement manually:

```text
IsCanOblation(color)
  -> decrement local Carry through GameModel::FDA889...
  -> build { color, sourceStationIndex }
  -> send normal Oblation message (507)
  -> authority updates Storage
  -> storage[color]++ through GameModel::FC6917...
  -> UI/color-complete callbacks
  -> StorageNum synchronization (513)
  -> F58184E938BDF8E80() four-color clear check
  -> next level or result flow
```

A normal caller in the public script passes `false, nil` for the final two arguments, which is the argument form used by the experimental patch for a local delivery attempt.

## 513 is not just a raw integer assignment

The storage receiver takes an incoming four-color storage state, compares it with the previous local four-color values, updates the game model and emits per-color UI/completion updates where values changed.

Therefore:

```text
BAD:  storage[color] = required[color]
GOOD: perform the normal delivery operation and allow 513 synchronization
```

A direct write can leave peers, UI, statistics, feedback and level-transition state disagreeing with the visible table.

## Why the patch does not force round clear

Round completion is already encoded in the normal path:

1. final useful delivery increments `storage[color]`;
2. `IsJustNeedNumToStorageNum` / color-complete UI paths run;
3. `F58184E938BDF8E80` checks all four colors;
4. the original scene code chooses next level versus result.

The correct automation therefore makes the normal condition true instead of overwriting a boolean.

## Multiplayer risk model

Until runtime-validated on 4.0.0, use these assumptions conservatively:

- local leader/offline state can generate local Smart Balloon fruit through `F466...`;
- non-leader clients should not fabricate extra local fruit, because the authority path is 506→511;
- Auto Deposit on a client can reuse `TryOblation`, but burst-sending many 507 messages in one script tick may race normal synchronization;
- the patch therefore limits a non-leader client to one automatic delivery per received fruit event by default;
- Instant Round is restricted to offline/local-leader authority in the current patch.

These are implementation safeguards, not claims that every host/client timing detail has been proven.
