local scripts = '"${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/'
hl.on("hyprland.start", function()
  hl.exec_cmd(scripts .. 'SessionStartup.sh"')
end)
hl.on("monitor.added", function()
  -- Initial monitor events precede UWSM readiness; the session unit owns
  -- initial wallpaper startup. Later hotplug reuses that daemon.
  hl.exec_cmd('systemctl --user is-active --quiet graphical-session.target && ' .. scripts .. 'Wallpaper.sh"')
end)
