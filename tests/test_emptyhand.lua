-- Standalone runtime mocks for the PUBLIC Lua hook, not a game runtime test.
local patch_path = assert(arg_patch_path)
local attempts, can_calls, original_results = 0, 0, 0
local held, storage, required = 0, 0, 3
local online = false
local should_throw = false

C6D182891100F211D = {prototype={}}
C9FD31BF01E130013 = {prototype={}}
CBA116AC4A909C38C = {prototype={}}
CE506B90C88D90C92 = {S499E8689030B1B66 = function() return online end}

local hud = {}
function hud:FA3DF24554485BE54(row, color)
  assert(color == 0)
  if row == 0 then return held elseif row == 1 then return required
  elseif row == 2 then return storage end
end
local scene = {[19]=true, [14]={[1]=hud}}
local station = {[14]=scene, [8]=0}

function C9FD31BF01E130013.prototype.FD9E6D41945878085(self, color)
  can_calls = can_calls+1
  return held > 0
end
function C6D182891100F211D.prototype.F5F3E9041FE44C3C6(self, color, is_remote, source_station)
  attempts = attempts + 1
  if is_remote then return nil end  -- simplified mock of remote packet path
  if not self[14][1]:FD9E6D41945878085(color) then
    return nil
  end
  if should_throw then error('mock-original-failure') end
  if held > 0 then held = held-1 end
  storage = storage+1
  original_results = original_results+1
  return 'ok', nil, 42
end
function CBA116AC4A909C38C.prototype.F5F3E9041FE44C3C6(self, is_remote, st)
  return self[14]:F5F3E9041FE44C3C6(self[8], is_remote, st)
end
setmetatable(hud, {__index=C9FD31BF01E130013.prototype})
setmetatable(scene, {__index=C6D182891100F211D.prototype})
setmetatable(station, {__index=CBA116AC4A909C38C.prototype})

-- First load: must leave defaults with no mutation.
assert(loadfile(patch_path))()
local P = assert(OGRE_OUSTIN_EMPTYHAND)
assert(P.config.enabled == false and P.config.read_only == true)
assert(station:F5F3E9041FE44C3C6(false, nil) == nil)
assert(storage == 0 and held == 0)

-- Record a candidate in read-only mode, still never grant.
P.config.trace = true
local prev = #P.events
assert(station:F5F3E9041FE44C3C6(false, nil) == nil)
assert(storage == 0 and #P.events == prev + 1)
assert(P.events[#P.events].reason == 'read-only')

-- An arbitrary call to Scene.TryOblation must not get privileged.
P.config.enabled = true
P.config.read_only = false
assert(scene:F5F3E9041FE44C3C6(0, false, nil) == nil)
assert(storage == 0)

-- One original station interaction grants exactly one normal storage increment.
local a,b,c = station:F5F3E9041FE44C3C6(false, nil)
assert(a == 'ok' and b == nil and c == 42)
assert(held == 0 and storage == 1)
assert(hud:FD9E6D41945878085(0) == false) -- guard cleaned up
assert(P.events[#P.events].reason == 'storage-incremented')

-- No remote bypass; no online bypass; no unknown network bypass.
assert(station:F5F3E9041FE44C3C6(true, nil) == nil)
assert(storage == 1)
online = true
assert(station:F5F3E9041FE44C3C6(false, nil) == nil)
assert(storage == 1)
online = false
CE506B90C88D90C92.S499E8689030B1B66 = nil
assert(station:F5F3E9041FE44C3C6(false, nil) == nil)
assert(storage == 1)
CE506B90C88D90C92.S499E8689030B1B66 = function() return online end

-- Full color must not overfill.
storage = required
assert(station:F5F3E9041FE44C3C6(false, nil) == nil)
assert(storage == required)

-- Guard restored on throwing original.
storage = 0
should_throw = true
local ok, err = pcall(function() return station:F5F3E9041FE44C3C6(false, nil) end)
assert(not ok and tostring(err):find('mock-original-failure',1,true))
assert(P._station_guard == nil and P._allow_guard == nil)
assert(hud:FD9E6D41945878085(0) == false)
should_throw = false

-- Next stage should still behave normally and idempotent patch load.
assert(loadfile(patch_path))()
for i=1,required do
  assert(station:F5F3E9041FE44C3C6(false, nil) == 'ok')
end
assert(storage == required and held == 0)
assert(original_results == required+1)
print('PASS: default off; read-only; provenance; single delivery; full returns; offline; cleanup; replay')
