#!/usr/bin/env bash
set -euo pipefail
: "${XDG_RUNTIME_DIR:?Run inside Hyprland}"
config="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
state="${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe"
mkdir -p "$state"
exec >>"$state/session.log" 2>&1
exec 9>"$XDG_RUNTIME_DIR/hyprixe-session.lock"
flock -n 9 || exit 0
# Import after hl.env has configured the compositor's child environment.
dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE QT_QPA_PLATFORMTHEME QT_STYLE_OVERRIDE TERMINAL || true
systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP QT_QPA_PLATFORMTHEME QT_STYLE_OVERRIDE TERMINAL || true
"$config/scripts/Wallpaper.sh" 9>&- &
"$config/scripts/WaybarStartup.sh" 9>&- &
"$config/scripts/Polkit.sh" 9>&- &
if ! pgrep -u "$(id -u)" -x hypridle >/dev/null; then hypridle -c "$config/hypridle.conf" 9>&- & fi
if ! pgrep -u "$(id -u)" -x swaync >/dev/null; then swaync 9>&- & fi
"$config/scripts/ClipboardWatcher.sh" 9>&- &
