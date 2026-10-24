#!/usr/bin/env bash
set -euo pipefail
# One IPC snapshot keeps labels and addresses aligned even if a window closes.
clients=$(hyprctl clients -j | jq '[.[] | select(.mapped and (.hidden != true))]')
[[ $(jq length <<<"$clients") -gt 0 ]] || exit 0
if ! index=$(jq -r '.[] | "\(.class) — \(.title | gsub("[\\r\\n]"; " "))"' <<<"$clients" |
    rofi -config "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/rofi/config.rasi" -dmenu -i -p Fenêtres -format i); then exit 0; fi
[[ "$index" =~ ^[0-9]+$ ]] || exit 1
address=$(jq -er --argjson i "$index" '.[$i].address' <<<"$clients")
[[ "$address" =~ ^0x[0-9a-fA-F]+$ ]] || exit 1
hyprctl dispatch "hl.dsp.focus({ window = \"address:$address\" })"
