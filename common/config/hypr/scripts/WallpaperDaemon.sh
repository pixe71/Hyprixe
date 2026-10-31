#!/usr/bin/env bash
set -euo pipefail
# Run in the foreground so systemd owns the persistent wallpaper daemon.
# shellcheck source=/dev/null
source "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/profile.env"
exec awww-daemon
