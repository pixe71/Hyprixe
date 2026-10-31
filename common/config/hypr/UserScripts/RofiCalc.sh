#!/usr/bin/env bash
# ==================================================
#  KoolDots (2026)
#  Project URL: https://github.com/LinuxBeginnings
#  License: GNU GPLv3
#  SPDX-License-Identifier: GPL-3.0-or-later
# ==================================================
# /* Calculator (using qalculate) and rofi */
# /* Submitted by: https://github.com/JosephArmas */

rofi_theme="${XDG_CONFIG_HOME:-$HOME/.config}/hypr/rofi/config-calc.rasi"

# Dependency checks
for cmd in rofi qalc wl-copy; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        if command -v notify-send >/dev/null 2>&1; then
            notify-send -u critical "RofiCalc" "Missing required dependency: $cmd"
        else
            echo "Error: Missing required dependency: $cmd" >&2
        fi
        exit 1
    fi
done

: "${XDG_RUNTIME_DIR:?Run inside a Wayland session}"
exec 9>"$XDG_RUNTIME_DIR/hyprixe-calculator.lock"
flock -n 9 || exit 0

# main function
calc_result=""
result=""

while true; do
    mesg_args=()
    if [[ -n "$result" || -n "$calc_result" ]]; then
        mesg_args=(-mesg "$result      =    $calc_result")
    fi

    result=$(
        rofi -i -dmenu \
            -config "$rofi_theme" \
            "${mesg_args[@]}"
    )

    if [ $? -ne 0 ]; then
        exit 0
    fi

    if [ -n "$result" ]; then
        calc_result=$(qalc -t "$result")
        echo "$calc_result" | wl-copy
    fi
done
