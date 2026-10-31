#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
hypr="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
status=0
# A private CLI flag stays with this process; applications cannot inherit it.
uwsm app -t scope -- rofi -hyprixe-launcher \
    -config "$hypr/rofi/config-launcher.rasi" -show drun || status=$?
case "$status" in
    0|1) exit 0 ;;  # application launched or Escape
    10) exec "$hypr/scripts/LaunchApp.sh" dolphin ;;
    11) exec "$hypr/scripts/WindowSwitcher.sh" ;;
    12) exec "$hypr/scripts/LaunchTerminal.sh" ;;
    *) echo "ERROR: Rofi launcher failed (exit $status)" >&2; exit "$status" ;;
esac
