-- Common KoolDots settings, without GPU or resolution assumptions.
hl.config({
  general = { layout = "dwindle", resize_on_border = true },
  dwindle = { preserve_split = true },
  master = { new_status = "slave" },
  misc = { disable_hyprland_logo = true, force_default_wallpaper = 0 },
  binds = { workspace_back_and_forth = true, allow_workspace_cycles = true },
  xwayland = { force_zero_scaling = true },
})
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
