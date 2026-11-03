# Hyprixe documentation

This is the canonical, versioned documentation for Hyprixe. **Debian 13 Trixie**
is supported; NixOS is planned. The [project README](../README.md) is the short
introduction. Platform status belongs to one shared Hyprixe release.

## Install and use

| Guide | Contents |
| --- | --- |
| [Requirements](requirements.md) | Prerequisites, packages, supported version range and test tools |
| [Hyprland compatibility](hyprland-compatibility.md) | Shared minimum, reference versions and provisional future-version checks |
| [Installation](installation.md) | Native/VMware profiles, installer options and system changes |
| [First login](first-start.md) | SDDM session selection and initial checks |
| [Keybindings](keybindings.md) | Complete keyboard, mouse and gesture reference |
| [Verification](verification.md) | Source, dependency and live-session checks; meaning of SKIPPED |
| [Updating](update.md) | Pulling changes, redeployment and component restarts |
| [Uninstall and restore](uninstall-restore.md) | Dated transactions, conflict protection and recovery |

## Components

| Guide | Contents |
| --- | --- |
| [Waybar](waybar.md) | Module layout, tray, taskbar, hardware detection and compatibility build |
| [Rofi](rofi.md) | Applications, clipboard, window switcher and shared Frosted Glass theme |
| [Wlogout](wlogout.md) | Four actions, confirmations and UWSM logout |
| [Kitty, Zsh and Powerlevel10k](kitty-zsh.md) | Terminal, prompt, plugins, fonts and account shell |
| [Dolphin and Kvantum](dolphin-kvantum.md) | App-specific light glass paint and preserved interface |
| [SDDM](sddm.md) | Greeter theme, session chooser, system files and recovery |
| [Hyprlock and Hypridle](hyprlock-hypridle.md) | Locking, idle behaviour and presentation mode |
| [UWSM and session services](uwsm.md) | Session lifecycle, wallpaper, notifications and application scopes |

## Maintain and contribute

- [Customization](customization.md): change the repository first, then deploy.
- [Troubleshooting](troubleshooting.md): diagnose session, dependency and component failures.
- [Core and profiles](core-profiles.md): source ownership, platform boundaries and contribution rule.
- [Refactor validation](core-profiles-validation.md): v1 equivalence evidence and Debian PC acceptance.
- [Architecture](architecture.md): sources, deployment, service ownership and tests.
- [Release readiness](release-readiness.md): dated pre-v1 audit, asset caveats and acceptance checklist.
- [Screenshots](screenshots/README.md): existing captures and images still needed.
- [Wiki](wiki/Home.md): short installation, shortcut and troubleshooting pages.
- [Credits and provenance](../CREDITS.md): upstream projects and unresolved asset attribution.
- [Asset inventory](assets-provenance.md): identified sources, license evidence and publication blockers.

## Historical evidence

[Initial audit](AUDIT.md), [original change inventory](CHANGES.md),
[dated validation log](VALIDATION.md) and the [original file inventory](inventory-original.tsv)
are retained as historical evidence. They include earlier configurations and
test counts; they are not installation instructions or a description of every
current file. Current guides above take precedence.
