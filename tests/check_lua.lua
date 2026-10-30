-- Execute the complete native load graph with an explicit, recording hl API.
-- This checks load order, callbacks and duplicate chords; it is NOT Hyprland.
local config = assert(arg[1])
local binds, hooks, settings, dispatched = {}, {}, {}, {}
local workspaces = {}
local executed = {}
local window_snapshot, active_window, query_count = {}, nil, 0
local current_workspace, special_workspace = {id = 1}, nil
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
  dispatch = function(a)
    assert(a.name); dispatched[#dispatched+1] = a
    if a.name == "focus" and a.opts.window then
      for _, window in ipairs(window_snapshot) do
        if a.opts.window == "address:" .. window.address then active_window = window end
      end
    elseif a.name == "alter_zorder" then
      -- Mimic native z-order mutation, including a floating selected window.
      for i, window in ipairs(window_snapshot) do
        if a.opts.window == "address:" .. window.address then
          table.remove(window_snapshot, i); table.insert(window_snapshot, window); break
        end
      end
    end
  end,
  get_active_window = function() return active_window end,
  get_active_workspace = function() return current_workspace end,
  get_active_special_workspace = function() return special_workspace end,
  get_windows = function(query)
    assert(query.workspace == (special_workspace or current_workspace) and query.mapped == true)
    query_count = query_count + 1
    return window_snapshot
  end,
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
for _, name in ipairs({"close", "fullscreen", "float", "pseudo", "drag", "resize", "move", "alter_zorder"}) do
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
  "super + backspace", "super + mouse:272", "super + mouse:273", "super + left", "super + right", "super + up", "super + down", "alt + tab", "alt + shift + tab"}) do
  assert(binds[chord], "Missing chord: " .. chord)
end
assert(binds["super + mouse:272"].fn.name == "drag")
assert(not binds["super + mouse:272"].options.mouse, "Lua does not support opts.mouse")
for chord, mode in pairs({
  ["super + shift + s"] = "--copy-area", ["print"] = "--save", ["shift + print"] = "--save-area",
  ["super + print"] = "--now", ["super + shift + print"] = "--area",
}) do
  assert(binds[chord] and binds[chord].fn.opts:find('ScreenShot.sh" ' .. mode, 1, true), "Missing/conflicting screenshot binding: " .. chord)
end
assert(binds["super + mouse:273"].fn.name == "resize")
assert(binds["super + mouse:273"].fn.opts == nil, "Mouse resize must start interactive resizing, not a pixel step")
for chord, binding in pairs(binds) do
  assert(binding.options.description:sub(1, 10) == "Hyprixe | ", "Missing live-audit identity: " .. chord)
end
assert(binds["super + e"].fn.opts:find('LaunchApp.sh" dolphin', 1, true))
assert(KOOLDOTS_DEFAULTS.term == "kitty")
for _, chord in ipairs({"super + backspace", "super + shift + e"}) do
  assert(binds[chord] and binds[chord].fn.name == "exec_cmd" and binds[chord].fn.opts == "hyprixe-session",
    "Session shortcuts must use the same Wlogout helper: " .. chord)
end
assert(binds["super + space"].fn.opts:find('RofiLauncher.sh"', 1, true), "Application launcher changed")
for chord, binding in pairs(binds) do
  if type(binding.fn) == "table" and binding.fn.name == "exec_cmd" then
    assert(not binding.fn.opts:find("PowerMenu.sh", 1, true) and
      not binding.fn.opts:find("Logout.sh", 1, true) and
      not binding.fn.opts:find("Wlogout.sh", 1, true), "Legacy menu bind: " .. chord)
  end
end
assert(binds["super + return"].fn.opts:find('LaunchTerminal.sh"', 1, true))
assert(binds["super + return"].options.description == "Hyprixe | SUPER + Return | Kitty")
window_snapshot = {
  {address="0xa", stable_id=1, accepts_input=true},
  {address="0xb", stable_id=2, accepts_input=true, floating=true},
  {address="0xc", stable_id=3, accepts_input=true},
  {address="0xd", stable_id=4, accepts_input=true, hidden=true},
  {address="invalid", stable_id=5, accepts_input=true},
  {address="0xe", stable_id=6, accepts_input=false},
}
active_window = window_snapshot[1]
for _, address in ipairs({"0xb", "0xc", "0xa", "0xb"}) do
  local before = query_count
  binds["alt + tab"].fn()
  assert(active_window.address == address, "Forward cycle skipped a window after z-order changed")
  assert(query_count == before + 1, "Cycle must query one window snapshot")
  assert(dispatched[#dispatched-1].name == "alter_zorder" and dispatched[#dispatched].name == "focus")
end
for _, address in ipairs({"0xa", "0xc", "0xb"}) do
  binds["alt + shift + tab"].fn()
  assert(active_window.address == address, "Reverse cycle is not the inverse of forward cycling")
end
-- A closed selected window, empty workspace and single window are all bounded.
window_snapshot = {{address="0xa", stable_id=1, accepts_input=true}}
active_window = nil
binds["alt + shift + tab"].fn()
assert(active_window.address == "0xa")
local before = #dispatched
binds["alt + tab"].fn()
assert(#dispatched == before, "Single-window cycle must do nothing")
window_snapshot = {}
binds["alt + tab"].fn()
assert(#dispatched == before, "Empty-workspace cycle must do nothing")
-- Honor the visible special workspace, and permit focus behind fullscreen.
special_workspace = {id = -99}
window_snapshot = {
  {address="0xa", stable_id=1, accepts_input=true, fullscreen=2},
  {address="0xb", stable_id=2, accepts_input=false},
}
active_window = window_snapshot[1]
binds["alt + tab"].fn()
assert(active_window.address == "0xb", "Fullscreen-blocked windows must remain selectable")
special_workspace = nil
assert(hooks["hyprland.start"] and hooks["monitor.added"])
hooks["monitor.added"]()
assert(executed[#executed]:find('systemctl --user is-active --quiet graphical-session.target && ', 1, true), "Hotplug must wait for UWSM graphical readiness")
for _, callback in pairs(hooks) do callback() end
local count = 0
for _ in pairs(binds) do count = count + 1 end
print("PASS: Lua load graph, " .. count .. " unique chords, four persistent workspaces without monitor bindings, required shortcuts, both cycle directions, startup and hotplug callbacks (mock API)")
