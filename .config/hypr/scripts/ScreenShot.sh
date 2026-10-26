#!/usr/bin/env bash
# Capture helper derived from KoolDots (GPL-3.0-or-later).
set -euo pipefail
mode=${1:---now}
case "$mode" in
    --now|--save|--in5|--in10|--area|--copy-area|--save-area|--swappy|--swapp|--swap|--win|--active) ;;
    *) echo 'Usage: ScreenShot.sh --copy-area|--save|--save-area|--now|--area|--active|--in5|--in10|--swappy' >&2; exit 2 ;;
esac
command -v grim >/dev/null || { echo 'Missing screenshot dependency: grim' >&2; exit 1; }
if [[ $mode != --save && $mode != --save-area ]]; then
    command -v wl-copy >/dev/null || { echo 'Missing screenshot dependency: wl-copy' >&2; exit 1; }
fi
geometry=''
case "$mode" in
    --area|--copy-area|--save-area|--swappy|--swapp|--swap)
        command -v slurp >/dev/null || { echo 'Missing screenshot dependency: slurp' >&2; exit 1; }
        # Escape/cancellation leaves the clipboard and capture directory alone.
        geometry=$(slurp) || exit 0
        [[ -n $geometry ]] || exit 0 ;;
    --win|--active)
        geometry=$(hyprctl activewindow -j | jq -er 'select(.mapped) | "\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])"') ;;
esac
temporary=$(mktemp --suffix=.png)
file=''
keep_file=false
cleanup() {
    rm -f -- "$temporary"
    if [[ -n $file ]] && ! $keep_file; then rm -f -- "$file"; fi
}
trap cleanup EXIT
case "$mode" in
    --in5|--in10)
        seconds=${mode#--in}
        for ((i=seconds; i>0; i--)); do
            notify-send -t 1000 -i camera-photo "Capture dans $i s" || true
            sleep 1
        done
        ;;
esac
if [[ -n $geometry ]]; then grim -g "$geometry" "$temporary"; else grim "$temporary"; fi
[[ -s "$temporary" ]] || { echo 'Screenshot failed: grim produced no image.' >&2; exit 1; }
if [[ $mode == --copy-area ]]; then
    # Do not replace clipboard contents when capture fails.
    wl-copy --type image/png <"$temporary"
    notify-send -i camera-photo 'Capture copiée' || true
    exit 0
fi
if [[ $mode == --save || $mode == --save-area ]]; then
    directory="$HOME/Pictures/Screenshots"
else
    # Keep the existing SUPER+Print/editor behavior and XDG picture path.
    pictures=$(xdg-user-dir PICTURES 2>/dev/null || printf '%s/Pictures' "$HOME")
    directory="${pictures:-$HOME/Pictures}/Screenshots"
fi
mkdir -p "$directory"
# Atomically reserve a unique name, even for concurrent same-second captures.
file=$(mktemp --tmpdir="$directory" "Screenshot-$(date +%Y-%m-%d_%H-%M-%S)-XXXXXX.png")
if [[ $mode == --swap* ]]; then
    command -v swappy >/dev/null || { echo 'Install optional package swappy.' >&2; exit 1; }
    swappy -f "$temporary" -o "$file"
else
    cp -- "$temporary" "$file"
fi
[[ -s "$file" ]] || exit 0
keep_file=true
if [[ $mode == --save || $mode == --save-area ]]; then
    notify-send -i camera-photo 'Capture enregistrée' "$file" || true
    exit 0
fi
wl-copy --type image/png <"$file"
notify-send -i camera-photo 'Capture enregistrée et copiée' "$file" || true
