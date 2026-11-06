# Installation

## Requirements

- Debian 13 Trixie, working graphics drivers and a normal sudo-enabled account.
- Git, Bash and Python 3; network access and space for builds/backups on first install.
- SDDM with its **Qt 6 greeter already installed** (`sddm-greeter-qt6`).
  Hyprixe does not switch display managers or install GPU drivers for you.
- Hyprland **0.55.2 or later** with the Lua API. 0.55.2 and 0.56.2 are reference
  release numbers; other eligible builds remain provisional and must pass checks.
- Pinned shell assets support x86_64 and aarch64.

If basic tools or the greeter are missing, prepare them through Debian first:

```bash
sudo apt update
sudo apt install git python3 sddm sddm-theme-debian-breeze
command -v sddm sddm-greeter-qt6
```

## Install

Close Dolphin and finish file transfers. Run as your desktop user, **not root**:

```bash
git clone https://github.com/pixe71/hyprixe-debian.git
cd hyprixe-debian
./install.sh native
```

A normal install prepares Debian/backports packages and compatible Rofi, Waybar,
awww and Wallust when needed. It installs verified prompt/font assets, backs up
managed files, deploys the desktop and SDDM, then changes the account shell to Zsh.
SDDM is not restarted and you are not logged out automatically.

## Options

| Option | Purpose |
| --- | --- |
| `native` | Default hardware profile |
| `vmware` | Same desktop with isolated VM graphics adaptations and guest packages |
| `--dry-run` | Preview without writing configuration, backups or packages |
| `--no-packages` | Reuse already prepared dependencies and verified assets; not a first-install shortcut |
| `--waybar-only` | Update the bar and its font without package/shell/SDDM changes |
| `--dolphin-only` | Update Dolphin paint while preserving its interface |

Scoped modes are mutually exclusive. Use `./install.sh --help` for all options.
Custom XDG deployment roots must remain inside your HOME; spaces are supported.
Unrelated personal files are preserved. Backups and restore are in [Maintenance](Maintenance#restore).

## First login

Save work and reboot after the first full installation. In SDDM select
**Hyprland (uwsm-managed)**, then open Kitty with `SUPER + Return`:

```bash
hyprctl version
hyprctl configerrors
uwsm check is-active -v compositor-only
systemctl --user is-active graphical-session.target hyprixe-session.target
./verify.sh --dependencies --session
```

`configerrors` should be empty; the targets should be active. The wallpaper
oneshot service can normally show `active (exited)`. Successful verification ends
with `RESULT: 0 failed check(s)`; see [Troubleshooting](Troubleshooting) for failures.

Check launcher/clipboard/window menus, audio, four persistent workspaces, the
current wallpaper and `SUPER + L` with a real password unlock. The default
keyboard is French AZERTY (`fr`, `latin9`); see [Keybindings](Keybindings).

A whole-session reconnect is required after shell/environment changes;
`hyprctl reload` alone cannot replace an inherited login environment.
