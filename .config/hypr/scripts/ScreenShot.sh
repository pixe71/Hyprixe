#!/usr/bin/env bash
# Capture helper derived from KoolDots (GPL-3.0-or-later).
set -euo pipefail
pictures=$(xdg-user-dir PICTURES 2>/dev/null || printf '%s/Pictures' "$HOME")
directory="$pictures/Screenshots"
mkdir -p "$directory"
file="$directory/Screenshot_$(date +%Y%m%d_%H%M%S)_$RANDOM.png"
temporary=$(mktemp --suffix=.png)
trap 'rm -f -- "$temporary"' EXIT
case "${1:---now}" in
    --now) grim "$temporary" ;;
    --in5|--in10)
        seconds=${1#--in}
        for ((i=seconds; i>0; i--)); do
            notify-send -t 1000 -i camera-photo "Capture dans $i s" || true
            sleep 1
        done
        grim "$temporary" ;;
    --area|--swappy|--swapp|--swap)
        geometry=$(slurp) || exit 0
        grim -g "$geometry" "$temporary" ;;
    --win|--active)
        geometry=$(hyprctl activewindow -j | jq -er 'select(.mapped) | "\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])"')
        grim -g "$geometry" "$temporary" ;;
    *) echo 'Usage: ScreenShot.sh --now|--area|--active|--in5|--in10|--swappy' >&2; exit 2 ;;
esac
[[ -s "$temporary" ]] || exit 1
if [[ ${1:-} == --swap* ]]; then
    command -v swappy >/dev/null || { echo 'Install optional package swappy.' >&2; exit 1; }
    swappy -f "$temporary" -o "$file"
else
    cp -- "$temporary" "$file"
fi
wl-copy --type image/png <"$file"
notify-send -i camera-photo 'Capture enregistrée et copiée' "$file" || true
