#!/usr/bin/env bash
set -euo pipefail
exec rofi -config "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/rofi/config.rasi" -show drun
