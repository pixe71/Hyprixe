#!/usr/bin/env bash
set -euo pipefail
: "${XDG_RUNTIME_DIR:?Run inside Hyprland}"
state="${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe"
mkdir -p "$state"
exec >>"$state/session.log" 2>&1
exec 9>"$XDG_RUNTIME_DIR/hyprixe-session.lock"
flock -n 9 || exit 0
if ! uwsm check is-active compositor-only; then
    echo 'ERROR: Select "Hyprland (uwsm-managed)" in SDDM, then log in again.' >&2
    echo 'Importing environment variables does not activate graphical-session.target.' >&2
    exit 1
fi
# Finalize from the compositor's child environment after hl.env. UWSM owns
# activation/cleanup of graphical-session.target; never start it ourselves.
uwsm finalize HYPRLAND_INSTANCE_SIGNATURE PATH TERMINAL XDG_CURRENT_DESKTOP XDG_SESSION_TYPE \
    QT_QPA_PLATFORM QT_QPA_PLATFORMTHEME QT_STYLE_OVERRIDE QT_QUICK_CONTROLS_STYLE \
    QT_WAYLAND_DISABLE_WINDOWDECORATION MOZ_ENABLE_WAYLAND XCURSOR_THEME XCURSOR_SIZE
systemctl --user daemon-reload
# Services are ordered after UWSM's graphical target. Queue without blocking
# compositor startup while UWSM completes its readiness handshake.
systemctl --user start --no-block hyprixe-session.target
