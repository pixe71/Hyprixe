# NixOS profile: planned

This profile is not implemented. There is no working flake, Home Manager module
or installation command. Debian 13 remains the supported platform.

The next step will study Flakes/Home Manager consuming `common/` directly.
Do not copy shared Hyprland, Rofi, Waybar, shell, theme or wallpaper files here.
Use the central source/destination mappings and reproduce the Core contract:
SDDM -> Hyprland (uwsm-managed) -> graphical-session.target -> Hyprixe services.

Future platform integration must resolve package paths, Zsh plugin paths,
authentication-agent commands, greeter deployment and user-service declarations.
One Hyprixe Git release/version will cover all supported profiles.

Conceptually, updates may later use `git pull --ff-only` followed by
`sudo nixos-rebuild switch --flake ...`. This is not a functional Hyprixe
command today; no flake is supplied and planned status does not imply support.
