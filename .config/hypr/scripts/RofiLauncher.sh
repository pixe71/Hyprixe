#!/usr/bin/env bash
set -euo pipefail
exec uwsm app -- rofi -config "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/rofi/config.rasi" -show drun
