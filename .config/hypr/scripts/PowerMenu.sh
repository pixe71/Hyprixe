#!/usr/bin/env bash
set -euo pipefail
config="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
choice=$(printf 'Verrouiller\nSuspendre\nDéconnexion\nRedémarrer\nÉteindre\n' |
    rofi -config "$config/rofi/config.rasi" -dmenu -i -p Session) || exit 0
case "$choice" in
    Verrouiller) exec "$config/scripts/LockScreen.sh" ;;
    Suspendre) exec systemctl suspend ;;
    Déconnexion) hyprctl dispatch 'hl.dsp.exit()' ;;
    Redémarrer|Éteindre)
        confirm=$(printf 'Annuler\nConfirmer\n' | rofi -config "$config/rofi/config.rasi" -dmenu -p "$choice") || exit 0
        [[ "$confirm" == Confirmer ]] || exit 0
        if [[ "$choice" == Redémarrer ]]; then systemctl reboot; else systemctl poweroff; fi ;;
esac
