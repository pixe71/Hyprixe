-- Execute the complete native load graph with an explicit, recording hl API.
-- This checks load order, callbacks and duplicate chords; it is NOT Hyprland.
local config = assert(arg[1])
local binds, hooks, settings, dispatched = {}, {}, {}, {}
local workspaces = {}
local executed = {}
local function action(name)
  return function(opts) return { name = name, opts = opts } end
end
hl = {
  config = function(value) settings[#settings+1] = value end,
  env = function() end,
  monitor = function(rule) assert(rule.output == "", "Hardcoded output") end,
  workspace_rule = function(rule)
    assert(type(rule.workspace) == "string", "Workspace identifier must be a string")
    assert(not workspaces[rule.workspace], "Duplicate workspace rule")
    assert(rule.persistent == true, "Workspace must persist in the compositor")
    assert(rule.monitor == nil, "Workspace must not be pinned to an output")
    workspaces[rule.workspace] = rule
  end,
  curve = function() end,
  animation = function() end,
  gesture = function() end,
  window_rule = function() end,
  layer_rule = function() end,
  exec_cmd = function(command) executed[#executed+1] = command end,
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
local misc = {}
for _, setting in ipairs(settings) do
  for key, value in pairs(setting.misc or {}) do misc[key] = value end
end
assert(misc.background_color == "rgb(122434)", "Initial compositor background must match Frosted Glass")
assert(misc.disable_splash_rendering == true, "Built-in splash must not appear between greeter and wallpaper")
for id = 1, 4 do
  assert(workspaces[tostring(id)], "Missing persistent workspace " .. id)
end
local workspace_count = 0
for _ in pairs(workspaces) do workspace_count = workspace_count + 1 end
assert(workspace_count == 4, "Expected persistent workspace IDs 1 to 4")
for _, chord in ipairs({"super + return", "super + e", "super + space", "super + q", "super + l",
  "super + mouse:272", "super + mouse:273", "super + left", "super + right", "super + up", "super + down", "alt + tab", "alt + shift + tab"}) do
  assert(binds[chord], "Missing chord: " .. chord)
end
assert(binds["super + mouse:272"].options.mouse)
for chord, mode in pairs({
  ["super + shift + s"] = "--copy-area", ["print"] = "--save", ["shift + print"] = "--save-area",
  ["super + print"] = "--now", ["super + shift + print"] = "--area",
}) do
  assert(binds[chord] and binds[chord].fn.opts:find('ScreenShot.sh" ' .. mode, 1, true), "Missing/conflicting screenshot binding: " .. chord)
end
assert(binds["super + mouse:273"].options.mouse)
assert(binds["super + e"].fn.opts:find('LaunchApp.sh" dolphin', 1, true))
assert(KOOLDOTS_DEFAULTS.term == "alacritty")
binds["alt + tab"].fn()
assert(dispatched[1].name == "cycle_next" and dispatched[1].opts.next == true)
assert(dispatched[2].name == "alter_zorder")
binds["alt + shift + tab"].fn()
assert(dispatched[3].opts.next == false)
assert(hooks["hyprland.start"] and hooks["monitor.added"])
hooks["monitor.added"]()
assert(executed[#executed]:find('systemctl --user is-active --quiet graphical-session.target && ', 1, true), "Hotplug must wait for UWSM graphical readiness")
for _, callback in pairs(hooks) do callback() end
local count = 0
for _ in pairs(binds) do count = count + 1 end
print("PASS: Lua load graph, " .. count .. " unique chords, four persistent workspaces without monitor bindings, required shortcuts, both cycle directions, startup and hotplug callbacks (mock API)")
