# Troubleshooting

- Wrong SDDM session: reconnect using **Hyprland (uwsm-managed)**.
- Waybar missing: inspect its service and journal.
- Hyprland errors: check `configerrors`.
- Zsh not active after installation: log out of the desktop and back in.

```bash
hyprctl configerrors
systemctl --user status waybar.service
journalctl --user -u waybar.service -b
echo "$SHELL"
```

See the [full troubleshooting guide](https://github.com/pixe71/hyprixe-debian/blob/main/docs/troubleshooting.md).
