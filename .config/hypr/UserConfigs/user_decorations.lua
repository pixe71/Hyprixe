-- ==================================================
--  KoolDots (2026)
--  Project URL: https://github.com/LinuxBeginnings
--  License: GNU GPLv3
--  SPDX-License-Identifier: GPL-3.0-or-later
-- ==================================================
-- User decorations overrides.
-- Dynamically loads Wallust generated colors from wallust-hyprland.conf.

local home = os.getenv("HOME") or ""
local helper_path = home .. "/.config/hypr/lua/user_decorations_helper.lua"
local ok, helper = pcall(dofile, helper_path)
local wallust = (ok and helper and helper.load_wallust_colors)
  and helper.load_wallust_colors(home .. "/.config/hypr/wallust/wallust-hyprland.conf")
  or {}

local active_col = wallust.color12 or "rgba(8db4ffff)"
local inactive_col = wallust.color10 or "rgba(5f6578ff)"

-- Tokyo Night / Senshi inspired
-- VMware optimized
-- Frosted Glass / Senshi inspired
-- Adapted for current KoolDots Lua config

hl.config({
  general = {
    border_size = 2,
    gaps_in = 4,
    gaps_out = 10,

    col = {
      active_border = {
        colors = {
          "rgba(2770c0ff)",
          "rgba(1e4c84ff)",
        },
        angle = 45,
      },

      inactive_border = {
        colors = {
          "rgba(a44185cc)",
          "rgba(012339cc)",
        },
        angle = 45,
      },
    },
  },
})

hl.config({
  decoration = {
    rounding = 13,

    active_opacity = 0.78,
    inactive_opacity = 0.72,
    fullscreen_opacity = 1.0,

    shadow = {
      enabled = false,
    },

    blur = {
      enabled = true,
      size = 4,
      passes = 3,
      new_optimizations = true,
      ignore_opacity = true,
      xray = false,
      special = true,
      popups = true,
    },
  },
})
