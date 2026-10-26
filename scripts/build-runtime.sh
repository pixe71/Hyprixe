#!/usr/bin/env bash
set -euo pipefail
# Build missing applications or missing required capabilities. Builds run as the user.
# Binaries are staged, then backed up/deployed by deploy.py with the dotfiles.
output=${1:?Usage: build-runtime.sh STAGING_DIRECTORY}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
[[ -d "$output" ]] || { echo 'ERROR: staging directory must exist' >&2; exit 1; }
build=$(mktemp -d -t hyprixe-build.XXXXXXXX)
trap 'rm -rf -- "$build"' EXIT
install_build_dependencies() {
    local plan
    local -a packages
    # Do not use process substitution: a failed planner must stop installation.
    plan=$(python3 "$script_dir/apt-build-deps.py" "$1") || return 1
    mapfile -t packages <<<"$plan"
    sudo apt-get install -y --no-remove -o APT::Get::allow-Downgrades=false "${packages[@]}"
}
checkout() {
    local url=$1 commit=$2 name=$3
    git init -q "$build/$name"
    git -C "$build/$name" remote add origin "$url"
    git -C "$build/$name" fetch --depth 1 origin "$commit"
    git -C "$build/$name" checkout -q --detach FETCH_HEAD
    [[ $(git -C "$build/$name" rev-parse HEAD) == "$commit" ]] || exit 1
    git -C "$build/$name" submodule update --init --recursive --depth 1
}
if ! command -v awww >/dev/null || ! command -v awww-daemon >/dev/null; then
    echo 'Building awww v0.12.1 (pinned upstream commit).'
    install_build_dependencies awww
    sudo apt-get install -y -t trixie-backports cargo rustc
    checkout https://codeberg.org/LGFae/awww.git f66e12a76dbc4c669b2f1375f78bce49f5b19d66 awww
    (cd "$build/awww" && cargo build --release --locked)
    install -m755 "$build/awww/target/release/awww" "$output/awww"
    install -m755 "$build/awww/target/release/awww-daemon" "$output/awww-daemon"
fi
if ! python3 "$script_dir/waybar_compat.py"; then
    echo 'Preparing Waybar 0.12 with Lua workspace IPC and wlr/taskbar for Hyprland 0.56.2.'
    install_build_dependencies waybar
    checkout https://github.com/Alexays/Waybar.git 8490a1d9b9a5c8770dd63e9faca0a5e01acedcae waybar
    python3 "$script_dir/waybar_compat.py" --patch "$build/waybar"
    meson setup "$build/waybar/build" "$build/waybar" --buildtype=release --wrap-mode=nodownload \
        -Dman-pages=disabled -Dtests=disabled -Dlibnl=enabled -Dpulseaudio=enabled \
        -Dmpris=enabled -Ddbusmenu-gtk=enabled -Dexperimental=true
    meson compile -C "$build/waybar/build" -j 2
    install -m755 "$build/waybar/build/waybar" "$output/waybar"
fi
if ! python3 "$script_dir/rofi_compat.py"; then
    echo 'Building Rofi 2.0.0 with its native Wayland backend (Debian stable has X11 Rofi).'
    install_build_dependencies rofi
    checkout https://github.com/davatorium/rofi.git 0b6aa8ba8b4879f00c3cc96f2e47a13c079fe814 rofi
    meson setup "$build/rofi/build" "$build/rofi" --buildtype=release \
        -Dwayland=enabled -Dxcb=disabled -Dimdkit=false -Dcheck=disabled
    meson compile -C "$build/rofi/build"
    install -m755 "$build/rofi/build/rofi" "$output/rofi"
fi
