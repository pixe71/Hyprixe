# Wlogout Frosted Glass

`SUPER + Backspace` toggles a horizontal **Lock | Logout | Shutdown | Reboot**
menu. There are no Suspend or Hibernate buttons. The existing Waybar power
menu and every other shortcut retain their behavior.

## Appearance and sizing

The panel uses Hyprixe's `#122434` background at 0.76 alpha, `#e6f1f4` text,
subtle `#7ed6ff` borders and cyan hover/focus paint. Its exterior radius is
28 px. No action has a permanent active style. Four original monochrome SVGs
provide large icons above smaller JetBrains Mono labels; no additional font
or third-party icon/theme collection is downloaded.

The launcher queries the focused Hyprland output once and converts its mode,
scale and rotation into logical pixels. Equal margins leave a panel about
70% wide and 26% high. Wlogout uses four columns and zero column/row spacing;
it never switches to a 2x2 layout. Layer-shell chooses the focused output,
without fixed connector names, GDK monitor indices or stored resolutions.
The size is recalculated each time the menu opens.

Wlogout 1.2.2's layer namespace is **`logout_dialog`**, not `wlogout`. That
namespace joins the existing Hyprland blur rules. The translucent full-screen
surface softens the desktop behind the panel using the existing global blur;
global blur, window opacity and other applications' rules are unchanged.

## Launch and actions

The small executable `~/.local/bin/hyprixe-session` has two responsibilities:
responsive launch/toggle and dispatching the four fixed session actions.
The menu is a named transient UWSM **service**:

```text
uwsm app -s a -t service -u hyprixe-wlogout.service -- wlogout ...
```

It belongs to `app-graphical.slice`. A lock serializes launcher calls and the
stable unit name prevents duplicates. A second invocation stops only this
unit with `systemctl --user stop hyprixe-wlogout.service`; it does not kill
other Wlogout instances or the compositor. Escape closes Wlogout natively.

| Button | Action |
| --- | --- |
| Lock | Existing `hypr/scripts/LockScreen.sh`, including its duplicate guard and UWSM Hyprlock launch |
| Logout | Check that UWSM manages the compositor, confirm, then `uwsm stop` |
| Shutdown | Confirm, then `systemctl poweroff` |
| Reboot | Confirm, then `systemctl reboot` |

Destructive actions use the existing Frosted Glass Rofi configuration for a
small **Cancel / Confirm** prompt. Cancel is selected initially. Escape,
unexpected input and parser/launcher errors do not execute an action. The
dispatcher uses fixed argument lists, without `eval`, shell interpolation or
compositor kill commands. Wlogout closes its layer before running an action.

Use arrow keys to navigate, Enter to activate and Escape to dismiss. The
native direct keys are `l` (Lock), `e` (Logout), `s` (Shutdown), `r` (Reboot);
the last three still require confirmation.

The stylesheet declares GTK 3 navigation bindings on the window, mapping the
arrows to focus traversal and Enter/keypad Enter to the focused action.
GTK initially gives Lock keyboard focus; it is not a permanently styled
active button, and navigation moves the highlight to the current selection.

## Installation and restore

```bash
cd ~/hyprixe-debian
git pull
# Close Dolphin before running the existing full installer.
./install.sh native
hyprctl reload
hyprctl configerrors
./verify.sh --dependencies --session
```

Debian stable supplies `wlogout`; `librsvg2-common` supplies the GDK Pixbuf
loader for its SVG icons. Existing Python 3, Rofi, Hyprlock, UWSM and systemd
dependencies are reused. No build, backports addition or new session daemon
is needed for this feature. Open the menu with `SUPER + Backspace` or
`hyprixe-session`. No SDDM/session restart is required for the new shortcut.

The normal file-level deployment transaction backs up the existing Wlogout
files, helper, keybinds and layer rules. It handles custom XDG paths containing
spaces. Use `./uninstall.sh --list`, then `./uninstall.sh --backup=ID` for the
matching installation transaction and `hyprctl reload` to restore it. Unrelated
personal files in the Wlogout directory remain intact; Debian packages are
not removed automatically. No special recursive deletion is used.

`verify.sh` validates the four-object JSON stream used by Wlogout, order,
fixed commands, icons, GTK CSS (when the optional native parser is present),
the shortcut and blur namespace. Dependency/session modes additionally check
the deployed files, executable helper and required commands. The live binding
audit now expects 68 bindings, including `SUPER + Backspace`. The menu need
not be open for verification to succeed. Physical input and GPU blur remain
explicit interactive checks, not automated successes.

Upstream references: [Debian Wlogout CLI](https://manpages.debian.org/trixie/wlogout/wlogout.1.en.html),
[layout format](https://manpages.debian.org/trixie/wlogout/wlogout.5.en.html),
[Wlogout 1.2.2 source](https://github.com/ArtsyMacaw/wlogout/blob/1.2.2/main.c),
[UWSM lifecycle](https://github.com/Vladimir-csp/uwsm).
