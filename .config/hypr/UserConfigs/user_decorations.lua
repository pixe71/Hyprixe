-- ==================================================
--  KoolDots (2026)
--  Project URL: https://github.com/LinuxBeginnings
--  License: GNU GPLv3
--  SPDX-License-Identifier: GPL-3.0-or-later
-- ==================================================
-- Frosted Glass / Senshi inspired
-- Fixed palette: no wallpaper recolouring service changes these decorations.

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
