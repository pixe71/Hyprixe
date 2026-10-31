#!/usr/bin/env bash
set -euo pipefail
: "${XDG_RUNTIME_DIR:?Run this script inside a Wayland session}"
config="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
wallpaper="${XDG_DATA_HOME:-$HOME/.local/share}/hyprixe/wallpapers/min_forest.jpg"
[[ -s "$wallpaper" ]] || { printf 'Missing wallpaper: %s\n' "$wallpaper" >&2; exit 1; }
# shellcheck source=/dev/null
source "$config/profile.env"
managed=false
if command -v uwsm >/dev/null && uwsm check is-active compositor-only; then
    managed=true
    # monitor.added can precede hyprland.start/finalization. The session unit
    # will apply the initial image after UWSM makes its graphical target ready.
    if ! systemctl --user is-active --quiet graphical-session.target; then
        echo 'Wallpaper deferred until UWSM graphical-session.target is active.'
        exit 0
    fi
fi
exec 9>"$XDG_RUNTIME_DIR/hyprixe-wallpaper.lock"
flock 9
state="${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe"
mkdir -p "$state"
if ! awww query >/dev/null 2>&1; then
    if $managed; then
        # The persistent daemon belongs to the session, not to this short-lived
        # image-application process. systemd stops it with the UWSM session.
        systemctl --user start hyprixe-awww.service
    else
        # Keep the standalone wallpaper helper usable for manual diagnostics.
        awww-daemon 9>&- >>"$state/wallpaper.log" 2>&1 &
    fi
fi
# Wait for IPC and for newly connected outputs to be registered, bounded at 5s.
ready=false
for ((attempt=0; attempt<50; attempt++)); do
    if outputs=$(awww query 2>/dev/null) && monitors=$(hyprctl monitors -j | jq -er '.[].name'); then
        ready=true
        while IFS= read -r monitor; do
            if ! grep -Fq -- "$monitor:" <<<"$outputs"; then ready=false; break; fi
        done <<<"$monitors"
        $ready && break
    fi
    sleep 0.1
done
if ! $ready; then
    if $managed; then
        echo 'awww: outputs not ready after 5s; inspect journalctl --user -b -u hyprixe-awww.service -u hyprixe-wallpaper.service' >&2
    else
        printf 'awww: outputs not ready after 5s; see %s/wallpaper.log\n' "$state" >&2
    fi
    exit 1
fi
# Omitting --outputs applies the image to every detected output.
# This is the same static image at login and hotplug: present it immediately.
# A one-second fade needlessly exposes the daemon's initial/previous contents.
awww img --resize crop --transition-type none "$wallpaper"
