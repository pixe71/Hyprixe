#!/usr/bin/env bash
set -euo pipefail
: "${XDG_RUNTIME_DIR:?Run inside Hyprland}"
exec 9>"$XDG_RUNTIME_DIR/hyprixe-waybar.lock"
flock -n 9 || exit 0
if ! uwsm check is-active compositor-only || ! systemctl --user is-active --quiet graphical-session.target; then
    echo 'ERROR: Waybar requires an active UWSM graphical session. Select "Hyprland (uwsm-managed)" in SDDM.' >&2
    exit 1
fi
systemctl --user daemon-reload
exec systemctl --user start waybar.service
