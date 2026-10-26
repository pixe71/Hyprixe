-- Single binding source. Native Hyprland Lua dispatchers (0.55.2+).
local d, w = hl.dsp, hl.dsp.window
local scripts = '"${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/'
KOOLDOTS_BINDS = {}
local function bind(chord, action, opts)
  assert(not KOOLDOTS_BINDS[chord], "Duplicate binding: " .. chord)
  KOOLDOTS_BINDS[chord] = hl.bind(chord, action, opts)
end
local function script(name, args)
  return d.exec_cmd(scripts .. name .. '"' .. (args and (" " .. args) or ""))
end
bind("SUPER + Return", script("LaunchTerminal.sh"), { description = "Alacritty" })
bind("SUPER + E", script("LaunchApp.sh", KOOLDOTS_DEFAULTS.files), { description = "Dolphin" })
bind("SUPER + Space", script("RofiLauncher.sh"), { description = "Rofi" })
bind("SUPER + Q", w.close(), { description = "Close window" })
bind("SUPER + L", script("LockScreen.sh"), { description = "Hyprlock" })
bind("SUPER + F", w.fullscreen({ mode = "fullscreen" }))
bind("SUPER + SHIFT + F", w.fullscreen({ mode = "maximized" }))
bind("SUPER + V", w.float({ action = "toggle" }))
bind("SUPER + P", w.pseudo())
bind("SUPER + J", d.layout("togglesplit"))
bind("SUPER + mouse:272", w.drag(), { mouse = true })
bind("SUPER + mouse:273", w.resize(), { mouse = true })
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
-- One action chain per chord; alter_zorder makes floating windows visible.
local function cycle(next_window)
  return function()
    hl.dispatch(w.cycle_next({ next = next_window }))
    hl.dispatch(w.alter_zorder({ mode = "top" }))
  end
end
bind("ALT + Tab", cycle(true), { description = "Next window on current workspace" })
bind("ALT + SHIFT + Tab", cycle(false), { description = "Previous window on current workspace" })
bind("ALT + F10", script("WindowSwitcher.sh"), { description = "All windows (Rofi)" })
bind("SUPER + SHIFT + E", script("PowerMenu.sh"))
bind("SUPER + CTRL + V", script("ClipManager.sh"))
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
