-- OGRE_OUSTIN_PATCH_BEGIN
-- Ogre Oustin: scoped offline empty-hand delivery research proof of concept.
-- Based on public 3.0.1-era script identifiers. NOT validated on Violet 4.0.0.
-- Default OFF + READ-ONLY. Does not change required/storage or force CLEAR.
do
  assert(rawget(_ENV, "__OGRE_OUSTIN_PATCH_V1") == nil,
    "Ogre EmptyHand: cannot coexist with old Smart Balloon/Auto Deposit")

  if rawget(_ENV, "__OGRE_OUSTIN_EMPTYHAND_V1") == nil then
    local SceneClass = assert(rawget(_ENV, "C6D182891100F211D"), "missing scene class")
    local HudClass = assert(rawget(_ENV, "C9FD31BF01E130013"), "missing HUD class")
    local StationClass = assert(rawget(_ENV, "CBA116AC4A909C38C"), "missing station class")
    local NetworkClass = rawget(_ENV, "CE506B90C88D90C92")
    local Scene = assert(SceneClass.prototype, "missing scene prototype")
    local Hud = assert(HudClass.prototype, "missing HUD prototype")
    local Station = assert(StationClass.prototype, "missing station prototype")

    local OriginalTry = assert(Scene.F5F3E9041FE44C3C6, "missing Scene.TryOblation")
    local OriginalCan = assert(Hud.FD9E6D41945878085, "missing Hud.IsCanOblation")
    local OriginalStation = assert(Station.F5F3E9041FE44C3C6, "missing Station.Deliver")
    local unpack_values = assert(table.unpack or unpack, "missing unpack")
    local function pack(...) return {n = select("#", ...), ...} end

    local P = {
      config = {
        enabled = false,    -- set true ONLY after offline read-only validation
        read_only = true,   -- must also be false to allow changed CanOblation
        offline_only = true,
        trace = false,
      },
      events = {},
      _station_guard = nil,
      _allow_guard = nil,
    }

    local function record(event, color, before, after, reason)
      if not P.config.trace then return end
      local events = P.events
      if #events >= 128 then table.remove(events, 1) end
      events[#events + 1] = {
        event = event, color = color, before = before, after = after, reason = reason
      }
    end

    local function run_scoped(field, value, fn, ...)
      local prior = P[field]
      P[field] = value
      local results = pack(pcall(fn, ...))
      P[field] = prior
      if not results[1] then error(results[2], 0) end
      return unpack_values(results, 2, results.n)
    end

    local function network_status()
      local f = NetworkClass and NetworkClass.S499E8689030B1B66
      if type(f) ~= "function" then return nil end -- unknown => fail closed
      local ok, active = pcall(f)
      if not ok or type(active) ~= "boolean" then return nil end
      return active
    end

    local function fruit_state(scene, color)
      local game = scene and scene[14]
      local hud = game and game[1]
      local get = hud and hud.FA3DF24554485BE54
      if type(get) ~= "function" then return nil end
      local ok, held, required, storage = pcall(function()
        return get(hud, 0, color), get(hud, 1, color), get(hud, 2, color)
      end)
      if not ok or type(held) ~= "number" or type(required) ~= "number"
        or type(storage) ~= "number" then return nil end
      return hud, held, required, storage
    end

    function P.GetState(scene, color)
      return fruit_state(scene, color)
    end

    function P.GetEvents()
      return P.events
    end

    -- Only during an authorized, synchronous original Scene.TryOblation call.
    Hud.FD9E6D41945878085 = function(self, color)
      local g = P._allow_guard
      if g ~= nil and g.hud == self and g.color == color then
        return true
      end
      return OriginalCan(self, color)
    end

    -- Station-scoped provenance. Calls from arbitrary Lua code do not qualify.
    Station.F5F3E9041FE44C3C6 = function(self, is_remote, station)
      if is_remote ~= false or station ~= nil or P._station_guard ~= nil then
        return OriginalStation(self, is_remote, station)
      end
      local scene, color = self[14], self[8]
      if scene == nil or type(color) ~= "number" then
        return OriginalStation(self, is_remote, station)
      end
      return run_scoped("_station_guard", {scene = scene, color = color},
        OriginalStation, self, is_remote, station)
    end

    Scene.F5F3E9041FE44C3C6 = function(self, color, is_remote, source_station)
      local cfg = P.config
      if not cfg.enabled and not cfg.trace then
        return OriginalTry(self, color, is_remote, source_station)
      end
      local station_context = P._station_guard
      local valid_color = type(color) == "number" and color >= 0 and color < 4
        and color % 1 == 0
      local gameplay = self ~= nil and self[19] == true
      local station_origin = station_context ~= nil and station_context.scene == self
        and station_context.color == color
      if not valid_color or not gameplay or not station_origin or is_remote ~= false
        or source_station ~= nil or P._allow_guard ~= nil then
        return OriginalTry(self, color, is_remote, source_station)
      end
      local hud, held, required, stored = fruit_state(self, color)
      if hud == nil then return OriginalTry(self, color, is_remote, source_station) end
      local before = {held = held, required = required, stored = stored}
      local online = network_status()
      if online ~= false or not cfg.offline_only then
        record("skip", color, before, nil, online == nil and "network-unknown"
          or (online == true and "online" or "offline-only-required"))
        return OriginalTry(self, color, is_remote, source_station)
      end
      if held ~= 0 or stored < 0 or required <= 0 or stored >= required then
        record("skip", color, before, nil, "not-eligible")
        return OriginalTry(self, color, is_remote, source_station)
      end
      if not cfg.enabled or cfg.read_only then
        record("candidate", color, before, nil, "read-only")
        return OriginalTry(self, color, is_remote, source_station)
      end

      -- Caller remains in the real station's interaction and normal game flow.
      -- The one predicate is changed; no arrays, packets or clear flags are written.
      record("allow", color, before, nil, "scoped-empty-hand")
      local results = pack(pcall(function()
        return run_scoped("_allow_guard", {hud = hud, color = color},
          OriginalTry, self, color, is_remote, source_station)
      end))
      if not results[1] then error(results[2], 0) end
      local _, after_held, _, after_stored = fruit_state(self, color)
      if after_held ~= nil then
        record("result", color, before,
          {held = after_held, stored = after_stored},
          after_stored == stored + 1 and "storage-incremented" or "no-confirmed-progress")
      end
      return unpack_values(results, 2, results.n)
    end

    rawset(_ENV, "OGRE_OUSTIN_EMPTYHAND", P)
    rawset(_ENV, "__OGRE_OUSTIN_EMPTYHAND_V1", true)
  end
end
-- OGRE_OUSTIN_PATCH_END
