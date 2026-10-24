#!/usr/bin/env bash

mapfile -t ADDRESSES < <(
    hyprctl clients -j |
    jq -r '.[] | select((.mapped // false) == true) | .address'
)

mapfile -t WINDOWS < <(
    hyprctl clients -j |
    jq -r '.[] |
        select((.mapped // false) == true) |
        "\(.class)  —  \(.title)"'
)

[ "${#WINDOWS[@]}" -eq 0 ] && exit

INDEX="$(
    printf '%s\n' "${WINDOWS[@]}" |
    rofi -dmenu -i -p "Fenêtres" -format i
)"

[ -z "$INDEX" ] && exit

ADDRESS="${ADDRESSES[$INDEX]}"

hyprctl dispatch \
    "hl.dsp.focus({ window = \"address:${ADDRESS}\" })"

