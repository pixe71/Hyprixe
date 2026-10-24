-- Hyprixe Debian — Frosted Glass, based on KoolDots (GPL-3.0-or-later).
-- Only this explicit module list is loaded; extras/kooldots is never sourced.
local home = os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")
local base = home .. "/hypr/"
for _, name in ipairs({
  "UserConfigs/user_defaults.lua", "lua/env.lua", "profile.lua",
  "lua/settings.lua", "UserConfigs/user_settings.lua",
  "UserConfigs/user_decorations.lua", "lua/animations.lua",
  "UserConfigs/user_animations.lua", "lua/monitors.lua",
  "UserConfigs/monitors.lua", "lua/rules.lua", "lua/keybinds.lua",
  "UserConfigs/user_keybinds.lua", "lua/startup.lua",
}) do
  dofile(base .. name)
end
