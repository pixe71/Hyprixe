local scripts = '"${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/'
hl.on("hyprland.start", function()
  hl.exec_cmd(scripts .. 'SessionStartup.sh"')
end)
hl.on("monitor.added", function()
  hl.exec_cmd(scripts .. 'Wallpaper.sh"')
end)
