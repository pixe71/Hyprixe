#!/usr/bin/env bash
set -euo pipefail
# Match the installed session PATH, including when testing from a stale terminal.
export PATH="$HOME/.local/bin:$PATH"
for command in hyprctl jq rofi; do
    command -v "$command" >/dev/null || { echo "Window switcher: missing $command" >&2; exit 1; }
done
hypr="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
config="$hypr/rofi/config-windows.rasi"
[[ -r $config ]] || { echo "Window switcher: missing $config" >&2; exit 1; }
# One IPC snapshot keeps labels and addresses aligned even if a window closes.
clients=$(hyprctl clients -j | jq '[.[] | select(.mapped and (.hidden != true))]')
[[ $(jq length <<<"$clients") -gt 0 ]] || exit 0
if index=$(jq -r '.[] | "\(.class) — \(.title | gsub("[\\r\\n]"; " "))"' <<<"$clients" |
    rofi -hyprixe-launcher -config "$config" -dmenu -i -p Fenêtres -format i); then
    :
else
    status=$?
    # Native dmenu custom actions return 10 + action index (zero-based).
    # These sidebar requests close Rofi before opening an existing helper.
    case "$status" in
        1) exit 0 ;; # Escape/cancel; never focus a window.
        10) exec "$hypr/scripts/RofiLauncher.sh" ;;
        26) exec "$hypr/scripts/LaunchApp.sh" dolphin ;;
        28) exec "$hypr/scripts/LaunchTerminal.sh" ;;
    esac
    printf 'Window switcher: rofi failed (%s)\n' "$status" >&2
    exit "$status"
fi
[[ "$index" =~ ^[0-9]+$ ]] || exit 1
address=$(jq -er --argjson i "$index" '.[$i].address' <<<"$clients")
[[ "$address" =~ ^0x[0-9a-fA-F]+$ ]] || exit 1
# hyprctl can exit zero while returning a Lua error. Never report that as focus.
result=$(hyprctl dispatch "(function()
    hl.dispatch(hl.dsp.window.alter_zorder({ mode = \"top\", window = \"address:$address\" }))
    return hl.dsp.focus({ window = \"address:$address\" })
end)()")
[[ $result == ok ]] || { printf 'Window switcher: focus failed: %s\n' "$result" >&2; exit 1; }
