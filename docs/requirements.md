# Requirements

[Documentation index](README.md)

## Supported target

Hyprixe v1 targets **Debian 13 Trixie**, a real Linux desktop/laptop and
**Hyprland (uwsm-managed)** through SDDM. Native is the default profile. The
separate VMware profile is optional; other distributions, including NixOS,
are not supported installation targets for this version.

The Lua configuration requires **Hyprland 0.55.2 or later**. Both installer and
live audit use the [same version policy](hyprland-compatibility.md): reference
release numbers are 0.55.2 and 0.56.2; other eligible versions receive a
provisional warning and must pass the actual configuration/API checks. There
is no speculative upper bound and no claim that future versions are officially
validated. Check `hyprctl version` and complete [release acceptance](release-readiness.md).

Powerlevel10k's pinned prebuilt Linux gitstatus assets are prepared for x86_64
and aarch64. Unsupported architectures fail before the login shell changes.
Physical GPU, monitor, suspend/resume and PAM behaviour still require testing
on the target hardware.

## Required before running the installer

- A working Debian 13 installation, package repositories and Internet access
  for the first installation. Keep an existing usable desktop/TTY for recovery.
- Working Wayland/DRM graphics drivers and a systemd/logind/D-Bus user session.
  Hyprixe does not install proprietary GPU drivers or hardware firmware for you.
- A normal user account with its own HOME and working `sudo` privileges.
  Run `install.sh` as that user, **not as root**.
- Git, Bash and Python 3 to obtain and run the installer.
- **SDDM and its Qt 6 greeter already installed**. The full installer checks
  `sddm` and `sddm-greeter-qt6`; it does not choose a display manager for you.
- Enough free space for package installation, optional source builds and dated
  backups. Finish file operations and close Dolphin before a full deployment.

If these prerequisites are missing, install them through Debian first:

```bash
sudo apt update
sudo apt install git python3 sddm sddm-theme-debian-breeze
command -v sddm sddm-greeter-qt6
```

Selecting/enabling SDDM instead of another display manager is a separate Debian
administration step. Hyprixe does not switch display managers automatically.
If sudo access is missing, an administrator must set it up first; reconnect
after a new group membership before returning to the normal desktop account.

## Installed automatically by a normal full installation

| Source | Role |
| --- | --- |
| [packages.txt](../profiles/debian/packages/packages.txt) | Kitty, Bash, Zsh and its two plugins, Dolphin/KIO, Kvantum/Qt6, Waybar, Wlogout, Rofi, NetworkManager UI, Bluetooth, PipeWire, SwayNC, clipboard and screenshot tools, fonts and utilities |
| [packages-backports.txt](../profiles/debian/packages/packages-backports.txt) | Hyprland, UWSM, Hyprlock, Hypridle, Hyprland portal and Xwayland from `trixie-backports` |
| [packages-sddm.txt](../profiles/debian/packages/packages-sddm.txt) | Qt 6 QML modules used by the Hyprixe greeter |
| [packages-dolphin.txt](../profiles/debian/packages/packages-dolphin.txt) | Dependencies for the scoped Dolphin installation |
| [VMware packages](../profiles/debian/packages/vmware.txt) | Guest tools, only when that profile is selected |

The installer enables the official backports suite when necessary and selects
it for the Hyprland components. Source-build headers from an already backported
library family are selected consistently; it does not set a global backports
pin or downgrade XKB libraries to stable.

Distribution binaries are checked for capabilities, not just their names.
When needed, pinned builds of awww, Waybar and Rofi are prepared, including the
Waybar Lua workspace protocol and Rofi sidebar/image support used here.
Build dependencies are installed on demand. See [architecture](architecture.md).
Powerlevel10k and the Nerd symbol font are fetched from pinned upstream sources
with checksums; Zsh itself uses Debian packages.

## Optional and development dependencies

[packages-optional.txt](../profiles/debian/packages/packages-optional.txt) is an optional tool/reference
list, not an additional list installed automatically. The inherited calculator
example needs the official Debian package
[qalc](https://packages.debian.org/trixie/amd64/qalc/filelist), which provides
`/usr/bin/qalc`; it has no assigned default keybinding. Hardware tools such
as `ddcutil` are not required for the default desktop.

ShellCheck, Lua 5.4 tools, a C++ compiler, GTK/PyGObject, PyQt6 and Qt QML tooling
enable additional validation. They are not all required to launch Hyprixe.
Missing optional test tools produce `SKIPPED`, as described in
[verification](verification.md). Missing required runtime commands under
`--dependencies` produce a failure.
