#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=/dev/null
source "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/profile.env"
: "${XDG_RUNTIME_DIR:?Run this script inside a Wayland session}"
exec 9>"$XDG_RUNTIME_DIR/hyprixe-lock.lock"
flock -n 9 || exit 0
pgrep -u "$(id -u)" -x hyprlock >/dev/null && exit 0
uwsm app -- hyprlock -c "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/hyprlock.conf"
