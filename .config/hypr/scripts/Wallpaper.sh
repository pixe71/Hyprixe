#!/usr/bin/env bash
set -euo pipefail
: "${XDG_RUNTIME_DIR:?Run this script inside a Wayland session}"
config="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
wallpaper="${XDG_DATA_HOME:-$HOME/.local/share}/hyprixe/wallpapers/min_forest.jpg"
[[ -s "$wallpaper" ]] || { printf 'Missing wallpaper: %s\n' "$wallpaper" >&2; exit 1; }
# shellcheck source=/dev/null
source "$config/profile.env"
exec 9>"$XDG_RUNTIME_DIR/hyprixe-wallpaper.lock"
flock 9
state="${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe"
mkdir -p "$state"
if ! awww query >/dev/null 2>&1; then
    if command -v uwsm >/dev/null && uwsm check is-active compositor-only; then
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
    if outputs=$(awww query 2>/dev/null); then
        monitors=$(hyprctl monitors -j | jq -er '.[].name')
        ready=true
        while IFS= read -r monitor; do
            if ! grep -Fq -- "$monitor:" <<<"$outputs"; then ready=false; break; fi
        done <<<"$monitors"
        $ready && break
    fi
    sleep 0.1
done
$ready || { printf 'awww: outputs not ready after 5s; see %s/wallpaper.log\n' "$state" >&2; exit 1; }
# Omitting --outputs applies the image to every detected output.
awww img --resize crop --transition-type fade --transition-duration 1 "$wallpaper"
