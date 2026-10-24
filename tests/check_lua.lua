-- Execute the complete native load graph with an explicit, recording hl API.
-- This checks load order, callbacks and duplicate chords; it is NOT Hyprland.
local config = assert(arg[1])
local binds, hooks, settings, dispatched = {}, {}, {}, {}
local function action(name)
  return function(opts) return { name = name, opts = opts } end
end
hl = {
  config = function(value) settings[#settings+1] = value end,
  env = function() end,
  monitor = function(rule) assert(rule.output == "", "Hardcoded output") end,
  curve = function() end,
  animation = function() end,
  gesture = function() end,
  window_rule = function() end,
  layer_rule = function() end,
  exec_cmd = function() end,
  dispatch = function(a) assert(a.name); dispatched[#dispatched+1] = a end,
  on = function(event, fn) assert(not hooks[event]); hooks[event] = fn end,
  bind = function(chord, fn, options)
    local normalized = chord:lower()
    assert(not binds[normalized], "Duplicate chord: " .. chord)
    binds[normalized] = {fn = fn, options = options}
    return { set_enabled = function() end }
  end,
  dsp = { exec_cmd = action("exec_cmd"), focus = action("focus"), layout = action("layout"),
    window = {} },
}
for _, name in ipairs({"close", "fullscreen", "float", "pseudo", "drag", "resize", "move", "cycle_next", "alter_zorder"}) do
  hl.dsp.window[name] = action(name)
end
dofile(config .. "/hypr/hyprland.lua")
for _, chord in ipairs({"super + return", "super + e", "super + space", "super + q", "super + l",
  "super + mouse:272", "super + mouse:273", "super + left", "super + right", "super + up", "super + down", "alt + tab", "alt + shift + tab"}) do
  assert(binds[chord], "Missing chord: " .. chord)
end
assert(binds["super + mouse:272"].options.mouse)
assert(binds["super + mouse:273"].options.mouse)
assert(binds["super + e"].fn.opts == "dolphin")
assert(KOOLDOTS_DEFAULTS.term == "alacritty")
binds["alt + tab"].fn()
assert(dispatched[1].name == "cycle_next" and dispatched[1].opts.next == true)
assert(dispatched[2].name == "alter_zorder")
binds["alt + shift + tab"].fn()
assert(dispatched[3].opts.next == false)
assert(hooks["hyprland.start"] and hooks["monitor.added"])
for _, callback in pairs(hooks) do callback() end
local count = 0
for _ in pairs(binds) do count = count + 1 end
print("PASS: Lua load graph, " .. count .. " unique chords, required shortcuts, both cycle directions, startup and hotplug callbacks (mock API)")
