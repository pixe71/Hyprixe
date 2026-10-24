#!/usr/bin/env bash
set -euo pipefail
: "${XDG_RUNTIME_DIR:?Run inside Hyprland}"
exec 9>"$XDG_RUNTIME_DIR/hyprixe-waybar.lock"
flock -n 9 || exit 0
# Reuse a service already chosen by the user. Its managed drop-in supplies the
# same explicit paths, so an enabled default service cannot win a startup race.
if systemctl --user is-enabled --quiet waybar.service 2>/dev/null || systemctl --user is-active --quiet waybar.service 2>/dev/null; then
    systemctl --user daemon-reload
    systemctl --user start waybar.service
    exit 0
fi
if pgrep -u "$(id -u)" -x waybar >/dev/null; then exit 0; fi
config="${XDG_CONFIG_HOME:-$HOME/.config}/hypr/waybar"
waybar -c "$config/config" -s "$config/style.css"
