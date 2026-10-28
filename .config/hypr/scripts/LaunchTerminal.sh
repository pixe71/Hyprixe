#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=/dev/null
source "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/profile.env"
exec uwsm app -- kitty "$@"
