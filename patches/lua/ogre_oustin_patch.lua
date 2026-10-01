-- Ogre Oustin' experimental Lua patch
-- Target logic recovered from SV-Script-RE 3.0.1-era script semantics and
-- intended to be validated against a user-extracted 4.0.0 main script.
--
-- This patch deliberately reuses original business functions rather than
-- directly writing the 3x4 fruit matrix.

if rawget(_ENV, "__OGRE_OUSTIN_PATCH_V1") == nil then
  __OGRE_OUSTIN_PATCH_V1 = true

  local P = {}
  OGRE_OUSTIN_PATCH = P

  P.config = {
    smart_balloon = true,
    auto_deposit = true,
    instant_round_on_first_balloon = false,
    allow_online_host = true,
  }

  P._busy = false

  local SceneClass = rawget(_ENV, "C6D182891100F211D")
  assert(SceneClass ~= nil, "Ogre patch: C6D182891100F211D missing")
  local SceneProto = SceneClass.prototype
  assert(SceneProto ~= nil, "Ogre patch: scene prototype missing")

  local NetworkClass = rawget(_ENV, "CE506B90C88D90C92")

  local Original = {
    OnCrashBalloon = SceneProto.FCE25070892D46E56,
    GrantLocalFruit = SceneProto.F466EB120F65C4DF8,
    TryOblation = SceneProto.F5F3E9041FE44C3C6,
  }

  assert(Original.OnCrashBalloon ~= nil, "Ogre patch: OnCrashBalloon anchor missing")
  assert(Original.GrantLocalFruit ~= nil, "Ogre patch: GrantLocalFruit anchor missing")
  assert(Original.TryOblation ~= nil, "Ogre patch: TryOblation anchor missing")

  local function imin(a, b)
    if a < b then return a end
    return b
  end

  local function imax(a, b)
    if a > b then return a end
    return b
  end

  local function get_instance()
    return SceneClass.S032897EBFF9CC1F2
  end

  local function get_game_model(self)
    if self == nil then return nil end
    return self[14]
  end

  local function get_hud_model(self)
    local game = get_game_model(self)
    if game == nil then return nil end
    return game[1]
  end

  local function is_network_active()
    if NetworkClass == nil or NetworkClass.S499E8689030B1B66 == nil then
      return false
    end
    return NetworkClass.S499E8689030B1B66()
  end

  local function is_leader()
    if NetworkClass == nil or NetworkClass.S64B658FF91156B71 == nil then
      return false
    end
    return NetworkClass.S64B658FF91156B71()
  end

  function P.GetFruitState(self, color)
    local hud = get_hud_model(self)
    if hud == nil then return nil end

    -- Row 0 = Carry/Held, row 1 = Required, row 2 = Storage/Table.
    local held = hud:FA3DF24554485BE54(0, color)
    local required = hud:FA3DF24554485BE54(1, color)
    local storage = hud:FA3DF24554485BE54(2, color)
    local hold_cap = hud[2]
    local total_held = hud:F214C1CBB9948C146()

    return held, required, storage, hold_cap, total_held
  end

  function P.CanAuthoritativeGrant(self)
    if not is_network_active() then
      return true
    end
    if not P.config.allow_online_host then
      return false
    end
    return is_leader()
  end

  function P.GrantLocalFruit(self, color, count)
    count = count or 1
    local granted = 0
    local i = 0
    while i < count do
      i = i + 1
      Original.GrantLocalFruit(self, color)
      granted = granted + 1
    end
    return granted
  end

  function P.SmartFillColor(self, color)
    if not P.CanAuthoritativeGrant(self) then
      return 0, "not-authoritative"
    end

    local held, required, storage, hold_cap, total_held = P.GetFruitState(self, color)
    if held == nil then
      return 0, "state-unavailable"
    end

    local missing = imax(0, required - storage - held)
    local room = imax(0, hold_cap - total_held)
    local extra = imin(missing, room)

    if extra > 0 then
      P.GrantLocalFruit(self, color, extra)
    end

    return extra
  end

  function P.AutoDepositColor(self, color, drain_all)
    local held, required, storage = P.GetFruitState(self, color)
    if held == nil then return 0, "state-unavailable" end

    local need = imax(0, required - storage)
    local count = imin(held, need)

    -- A non-leader network client should avoid burst-sending many 507 packets
    -- in one Lua call. One normal offer per received fruit event is the safer
    -- default until 4.0.0 multiplayer timing is runtime-validated.
    if is_network_active() and not is_leader() and not drain_all then
      count = imin(count, 1)
    end

    local sent = 0
    local i = 0
    while i < count do
      i = i + 1
      local before = held
      Original.TryOblation(self, color, false, nil)
      local after = P.GetFruitState(self, color)
      if after == nil then break end
      held = after

      -- Offline/leader path should synchronously reduce Carry. If no progress
      -- is observed, stop instead of spinning forever.
      if held >= before and (not is_network_active() or is_leader()) then
        break
      end
      sent = sent + 1
    end

    return sent
  end

  local function complete_current_round_impl(self)
    local color = 0
    while color < 4 do
      local guard = 0
      while guard < 512 do
        guard = guard + 1

        local held, required, storage, hold_cap, total_held = P.GetFruitState(self, color)
        if held == nil then
          return false, "state-unavailable"
        end
        if storage >= required then
          break
        end

        if held <= 0 then
          local missing = imax(0, required - storage - held)
          local room = imax(0, hold_cap - total_held)
          local grant = imin(missing, room)
          if grant <= 0 then
            return false, "no-carry-room"
          end
          P.GrantLocalFruit(self, color, grant)
          held = P.GetFruitState(self, color)
        end

        local before_held = held
        Original.TryOblation(self, color, false, nil)
        local after_held = P.GetFruitState(self, color)
        if after_held == nil then
          return false, "state-unavailable-after-oblation"
        end

        if after_held >= before_held then
          return false, "oblation-made-no-progress"
        end
      end
      color = color + 1
    end

    -- Do NOT set a clear flag. The final normal storage increment must make
    -- CA2A924A55DC1CE8A::F58184E938BDF8E80 return true naturally.
    return true
  end

  function P.CompleteCurrentRound(self)
    self = self or get_instance()
    if self == nil then
      return false, "scene-instance-unavailable"
    end
    if not P.CanAuthoritativeGrant(self) then
      return false, "not-authoritative"
    end
    if P._busy then
      return false, "busy"
    end

    P._busy = true
    local old_auto = P.config.auto_deposit
    P.config.auto_deposit = false
    local ok, reason = complete_current_round_impl(self)
    P.config.auto_deposit = old_auto
    P._busy = false
    return ok, reason
  end

  -- Auto Deposit hook. This executes after a normal local/received GetKinomi
  -- grant and reuses the original TryOblation path.
  SceneProto.F466EB120F65C4DF8 = function(self, color)
    local ret = Original.GrantLocalFruit(self, color)
    if P.config.auto_deposit and not P._busy then
      P.AutoDepositColor(self, color, false)
    end
    return ret
  end

  -- Smart Balloon hook. Original OnCrashBalloon runs first, preserving the
  -- normal 506/511 path. Extra local grants are only generated when this
  -- machine is offline or authoritative leader.
  SceneProto.FCE25070892D46E56 = function(self, crash_event, color)
    local ret = Original.OnCrashBalloon(self, crash_event, color)

    if P.config.instant_round_on_first_balloon and not P._busy then
      P.CompleteCurrentRound(self)
      return ret
    end

    if P.config.smart_balloon and not P._busy and P.CanAuthoritativeGrant(self) then
      P._busy = true
      P.SmartFillColor(self, color)
      if P.config.auto_deposit then
        P.AutoDepositColor(self, color, true)
      end
      P._busy = false
    end

    return ret
  end
end
-- OGRE_OUSTIN_PATCH_END
