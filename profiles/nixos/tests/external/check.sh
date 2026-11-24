#!/bin/sh
set -eu

repo=$(cd "$(dirname "$0")/../../../.." && pwd)
fixture="path:$repo/profiles/nixos/tests/external"

external_nix() {
    nix "$@" --no-write-lock-file --override-input hyprixe "path:$repo"
}

external_nix flake check "$fixture"
for host in disabled desktop two static dynamic; do
    external_nix eval --raw "$fixture#nixosConfigurations.$host.config.system.build.toplevel.drvPath"
    printf '\n'
done

invalid() {
    if result=$(external_nix eval --raw "$fixture#lib.invalid.$1.config.system.build.toplevel.drvPath" 2>&1); then
        printf 'Unexpected success for %s\n' "$1" >&2
        exit 1
    fi
    if ! printf '%s\n' "$result" | grep -F -- "$2"; then
        printf '%s\n' "$result" >&2
        exit 1
    fi
}
invalid noCompositor 'requires NixOS Hyprland with UWSM and Hyprlock PAM'
invalid duplicateWaybar 'Hyprixe manages Waybar'
invalid duplicateKitty 'Hyprixe manages Kitty'
invalid duplicateZsh 'Hyprixe deploys its canonical .zshrc'
invalid duplicateHyprland 'Hyprixe manages hyprland.lua'
invalid missingSddm 'requires the host to enable services.displayManager.sddm'
invalid reservedPublisher 'hyprixe-theme is reserved for the isolated Hyprixe SDDM receiver'
for host in missingTheme emptyPolicy unknownPublisher; do
    invalid "$host" 'requires the Hyprixe greeter and a list of declared local, normal users'
done
