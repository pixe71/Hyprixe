-- Single binding source. Native Hyprland Lua dispatchers (0.55.2+).
local d, w = hl.dsp, hl.dsp.window
local scripts = '"${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/'
KOOLDOTS_BINDS = {}
-- hyprctl's JSON omits display_key/enabled for Lua binds (and code:N keys).
-- Stable descriptions + the retained handles allow a real session audit.
HYPRIXE_KEYBINDS_REVISION = 1
local function bind(chord, action, opts)
  assert(not KOOLDOTS_BINDS[chord], "Duplicate binding: " .. chord)
  opts = opts or {}
  opts.description = "Hyprixe | " .. chord .. (opts.description and (" | " .. opts.description) or "")
  KOOLDOTS_BINDS[chord] = hl.bind(chord, action, opts)
end
local function script(name, args)
  return d.exec_cmd(scripts .. name .. '"' .. (args and (" " .. args) or ""))
end
bind("SUPER + Return", script("LaunchTerminal.sh"), { description = "Kitty" })
bind("SUPER + E", script("LaunchApp.sh", KOOLDOTS_DEFAULTS.files), { description = "Dolphin" })
bind("SUPER + Space", script("RofiLauncher.sh"), { description = "Rofi" })
bind("SUPER + Q", w.close(), { description = "Close window" })
bind("SUPER + L", script("LockScreen.sh"), { description = "Hyprlock" })
bind("SUPER + F", w.fullscreen({ mode = "fullscreen" }))
bind("SUPER + SHIFT + F", w.fullscreen({ mode = "maximized" }))
bind("SUPER + V", w.float({ action = "toggle" }))
bind("SUPER + P", w.pseudo())
bind("SUPER + J", d.layout("togglesplit"))
-- Lua uses the drag/resize dispatchers; opts.mouse is a legacy flag that
-- hl.bind does not read in 0.55.2/0.56.2. mouse=false in IPC is expected here.
bind("SUPER + mouse:272", w.drag())
bind("SUPER + mouse:273", w.resize())
for _, direction in ipairs({ "left", "right", "up", "down" }) do
  bind("SUPER + " .. direction, d.focus({ direction = direction }))
  bind("SUPER + SHIFT + " .. direction, w.move({ direction = direction }))
  local x = direction == "left" and -50 or (direction == "right" and 50 or 0)
  local y = direction == "up" and -50 or (direction == "down" and 50 or 0)
  bind("SUPER + CTRL + " .. direction, w.resize({ x = x, y = y, relative = true }), { repeating = true })
end
-- Physical keycodes work on the default French AZERTY layout as well as QWERTY.
for i = 1, 10 do
  local key = "code:" .. (i + 9)
  bind("SUPER + " .. key, d.focus({ workspace = i }))
  bind("SUPER + SHIFT + " .. key, w.move({ workspace = i }))
end
bind("SUPER + mouse_down", d.focus({ workspace = "e+1" }))
bind("SUPER + mouse_up", d.focus({ workspace = "e-1" }))
bind("SUPER + Page_Down", d.focus({ workspace = "e+1" }))
bind("SUPER + Page_Up", d.focus({ workspace = "e-1" }))
-- cycle_next iterates z-order, which alter_zorder changes after each step.
-- A stable native snapshot avoids skipping windows when raising the selection.
for _, name in ipairs({ "get_windows", "get_active_window", "get_active_workspace", "get_active_special_workspace" }) do
  assert(type(hl[name]) == "function", "Missing Hyprland Lua query: " .. name)
end
local function cycle(next_window)
  return function()
    local workspace = hl.get_active_special_workspace() or hl.get_active_workspace()
    if not workspace then return end
    local active = hl.get_active_window()
    local fullscreen = active and active.fullscreen and active.fullscreen ~= 0
    local windows = {}
    -- One synchronous query; copy scalar identifiers before dispatching anything.
    for _, window in ipairs(hl.get_windows({ workspace = workspace, mapped = true })) do
      if not window.hidden and (window.accepts_input or fullscreen) then
        local address, id = window.address, window.stable_id
        if type(address) == "string" and address:match("^0x%x+$") and type(id) == "number" then
          windows[#windows + 1] = { address = address, id = id }
        end
      end
    end
    if #windows == 0 then return end
    table.sort(windows, function(a, b) return a.id < b.id end)
    local index = next_window and 0 or (#windows + 1)
    for i, window in ipairs(windows) do
      if active and window.address == active.address then index = i; break end
    end
    local target = windows[((index - 1 + (next_window and 1 or -1)) % #windows) + 1]
    if active and target.address == active.address then return end
    -- Raise first, then focus/warp: the final action owns the keyboard focus.
    local selector = "address:" .. target.address
    hl.dispatch(w.alter_zorder({ mode = "top", window = selector }))
    hl.dispatch(d.focus({ window = selector }))
  end
end
bind("ALT + Tab", cycle(true), { description = "Next window on current workspace" })
bind("ALT + SHIFT + Tab", cycle(false), { description = "Previous window on current workspace" })
bind("ALT + F10", script("WindowSwitcher.sh"), { description = "All windows (Rofi)" })
bind("SUPER + SHIFT + E", script("PowerMenu.sh"))
bind("SUPER + CTRL + V", script("ClipManager.sh"))
bind("SUPER + SHIFT + S", script("ScreenShot.sh", "--copy-area"), { description = "Copy screenshot of selected area" })
bind("Print", script("ScreenShot.sh", "--save"), { description = "Save full screenshot" })
bind("SHIFT + Print", script("ScreenShot.sh", "--save-area"), { description = "Save screenshot of selected area" })
bind("SUPER + Print", script("ScreenShot.sh", "--now"))
bind("SUPER + SHIFT + Print", script("ScreenShot.sh", "--area"))
bind("XF86AudioRaiseVolume", d.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
bind("XF86AudioLowerVolume", d.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { locked = true, repeating = true })
bind("XF86AudioMute", d.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true })
bind("XF86AudioMicMute", d.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked = true })
bind("XF86AudioPlay", d.exec_cmd("playerctl play-pause"), { locked = true })
bind("XF86AudioNext", d.exec_cmd("playerctl next"), { locked = true })
bind("XF86AudioPrev", d.exec_cmd("playerctl previous"), { locked = true })
bind("XF86MonBrightnessUp", d.exec_cmd("brightnessctl set +5%"), { repeating = true })
bind("XF86MonBrightnessDown", d.exec_cmd("brightnessctl set 5%-"), { repeating = true })
