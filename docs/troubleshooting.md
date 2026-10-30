# Troubleshooting

[Documentation index](README.md)

Run commands from the checkout as the desktop user. Do not restart SDDM while
unsaved work is open. Begin with `./verify.sh --dependencies --session` inside
the intended graphical session and read the first relevant failure.

## Wrong SDDM session / Waybar dependency failure

A working compositor does not prove a UWSM session is active:

```bash
uwsm check is-active -v compositor-only
systemctl --user is-active graphical-session.target hyprixe-session.target
systemctl --user status waybar.service --no-pager
systemctl --user cat waybar.service
```

If the graphical target is inactive or Waybar reports a dependency failure,
save work, log out and choose **Hyprland (uwsm-managed)** in SDDM. Do not
manually start the graphical target or remove Debian's Waybar `Requisite`.
Hyprixe uses `hyprixe-session.target`; it does not depend on a vendor
`hyprland-session.target` existing.

## Waybar config, workspace or tray problems

```bash
journalctl --user -b -u waybar.service --no-pager
./verify.sh --waybar --session
systemctl --user restart waybar.service
systemctl --user status waybar.service --no-pager
```

The service must use the explicit `waybar/configs/Frosted-Glass` JSON and
`waybar/style.css`. There is deliberately no legacy `waybar/config` relay.
Four persistent workspaces require both the Lua persistence rules and the
Waybar list. Native Lua IPC, taskbar and click-drawer capabilities are checked;
a normal full install prepares a compatible binary if needed. Empty tray,
absent battery or Bluetooth hardware are not reasons for Waybar to crash.

## Lua/configuration or shortcut failures

```bash
hyprctl version
hyprctl configerrors
hyprctl -j binds
./verify.sh --dependencies --session
```

After deploying a binding-only change, run `hyprctl reload` and inspect errors.
The live audit also checks enabled handles and modifiers because Lua bind JSON
can contain callback IDs instead of command bodies. Default workspace shortcuts
use physical number-row codes on the French keyboard. Alt+Tab cycles eligible
windows on the current workspace; use Alt+F10 for a cross-workspace list.

The shared version policy requires at least 0.55.2. Only 0.55.2 and 0.56.2 are
reference release numbers; other eligible versions warn rather than fail on
age alone. Actual missing API/configuration errors still fail the audit.
See [compatibility policy](hyprland-compatibility.md).

## Package/build failures

```bash
apt-cache policy hyprland uwsm libxkbcommon0 libxkbcommon-dev libxkbregistry0 libxkbregistry-dev
./verify.sh --dependencies
```

Use official Trixie/backports sources and keep runtime/development packages
consistent. The build-dependency selector detects already installed backported
source families, including XKB, and selects matching headers without requesting
downgrades. Read APT's proposed changes and the install error; do not add a
global backports pin to bypass a conflict. `--no-packages` cannot supply missing
builds, plugins or initial prompt downloads.

## Kitty still opens Bash / prompt or glyph errors

```bash
zsh --version
getent passwd "$(id -un)" | cut -d: -f7
echo "$SHELL"
ps -p $$ -o comm=
fc-match 'JetBrains Mono'
fc-match 'Symbols Nerd Font Mono'
```

If the account entry is Zsh but `$SHELL` is stale, reconnect the entire desktop
session. Kitty intentionally has no hardcoded `shell zsh`. Do not convert Bash
scripts or source `.bashrc` as Zsh. Personal `.zshenv`/`.zprofile` output or a
changed `ZDOTDIR` can break quiet startup; the installer diagnoses this before
changing the account shell. See [terminal setup](kitty-zsh.md).

## Rofi or clipboard/window selection

```bash
command -v rofi
rofi -version
systemctl --user status hyprixe-clipboard.service --no-pager
journalctl --user -b -u hyprixe-clipboard.service --no-pager
./verify.sh --dependencies --session
```

Hyprixe's compatible Wayland binary under `~/.local/bin` must precede an
incompatible system Rofi. A Wayland session/display is needed for native parser
checks; an X11 display error is not proof of invalid Rasi. All active menus
share the common glass theme. Escape/error in the switcher must not focus a
window. See [Rofi](rofi.md) before changing its output/index handling.

## Wlogout

```bash
command -v wlogout hyprixe-session
systemctl --user status hyprixe-wlogout.service --no-pager
```

The named transient service exists only while the menu runs; absent/inactive
while closed is normal. Both session shortcuts toggle the same helper.
Logout requires an active UWSM compositor and uses `uwsm stop` after confirmation.
Do not replace it with a compositor kill. See [Wlogout](wlogout.md).

## Dolphin style or compositor blur

```bash
./verify.sh --dolphin --session
hyprctl getoption decoration:blur:enabled
systemctl --user show-environment | grep '^QT_STYLE_OVERRIDE='
```

`bool: true` is a valid enabled-blur response; older numeric output is also
handled. Dolphin needs Qt6 Kvantum, its app-specific theme association, the KDE
colour scheme and `QT_STYLE_OVERRIDE=kvantum` in the UWSM environment. Reconnect
after changing that environment. Close Dolphin before redeploying paint; do
not force another layout or make every application transparent as a workaround.

## Missing wallpaper / white transition after login

```bash
systemctl --user status hyprixe-awww.service hyprixe-wallpaper.service --no-pager
journalctl --user -b -u hyprixe-awww.service -u hyprixe-wallpaper.service -u waybar.service --no-pager -o short-monotonic
systemd-analyze --user critical-chain hyprixe-session.target
sudo journalctl -b -u sddm --no-pager -o short-monotonic
./verify.sh --session --diagnostics
```

Compare greeter shutdown, compositor readiness and wallpaper service timing;
inspect clients/layers for an actual blank fullscreen application. Wallpaper
is ordered before desktop services and waits for daemon readiness within a
bound. Do not add arbitrary sleeps or repeatedly kill/restart awww. A wallpaper
service can be restarted without replacing the daemon:

```bash
systemctl --user restart hyprixe-wallpaper.service
```

Physical login frames still require observation. Diagnostics can include
window titles and host details; review them before sharing.

## SDDM virtual keyboard or broken greeter

Run `./verify.sh --sddm`. The effective `[General] InputMethod=` must be empty;
the Hyprixe QML does not force a keyboard panel. A higher-priority local SDDM
setting can override snippets; the installer handles its managed keys with
backups. Reboot safely to refresh the greeter. For recovery from a TTY, use
the documented [SDDM-only restore](sddm.md#restore-only-the-greeter), without
deleting other themes or session entries.

## Restore refuses a changed file

This protects work saved after installation. Inspect the selected backup,
preserve personal changes and follow [restore](uninstall-restore.md). Do not
change file permissions or remove conflict checks just to force a passing test.
