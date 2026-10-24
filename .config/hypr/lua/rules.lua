-- Qt Widgets transparency is supplied by the unmodified Frosted-Glass Kvantum theme.
hl.window_rule({ name = "float-tools", match = { class = "^(pavucontrol|blueman-manager)$" }, float = true, center = true })
hl.window_rule({ name = "picture-in-picture", match = { title = "^([Pp]icture.in.[Pp]icture)$" }, float = true, pin = true })
for _, namespace in ipairs({ "rofi", "waybar", "swaync-control-center", "swaync-notification-window" }) do
  hl.layer_rule({ name = "frosted-" .. namespace, match = { namespace = namespace }, blur = true, ignore_alpha = 0 })
end
