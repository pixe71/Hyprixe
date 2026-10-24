#!/usr/bin/env bash

FROSTED="$HOME/Pictures/wallpapers/Frosted-Glass/min_forest.jpg"

[ -f "$FROSTED" ] || exit 1

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# VMware workaround
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
export GALLIUM_DRIVER=llvmpipe

# Restart awww only if it is not usable
if ! awww query >/dev/null 2>&1; then
    pkill -x awww-daemon 2>/dev/null || true
    awww-daemon >/tmp/awww-frosted.log 2>&1 &

    for i in $(seq 1 30); do
        awww query >/dev/null 2>&1 && break
        sleep 0.1
    done
fi

# Make Frosted the wallpaper remembered by KoolDots
ln -sfn "$FROSTED" "$HOME/.config/hypr/rofi/.current_wallpaper"
ln -sfn "$FROSTED" "$HOME/.config/hypr/rofi/.current_wallpaper_Virtual-1"

mkdir -p "$HOME/.config/hypr/wallpaper_effects"

cp -f "$FROSTED" "$HOME/.config/hypr/wallpaper_effects/.wallpaper_current"
cp -f "$FROSTED" "$HOME/.config/hypr/wallpaper_effects/.wallpaper_current_Virtual-1"

ln -sfn "$FROSTED" "$HOME/.config/hypr/wallpaper_effects/.hyprlock_current"

# Apply it
awww img -o Virtual-1 --resize crop "$FROSTED" \
    --transition-type fade \
    --transition-duration 1
