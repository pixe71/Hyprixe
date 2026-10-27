# Waybar organization with the existing Frosted Glass style

## Reference and actual differences

The actual [Hyprladus config.jsonc](https://github.com/sachatrouve1/Hyprladus/blob/main/config/waybar/config.jsonc)
and its `scripts/cpu-temp.sh` were read. It places a `group/traygroup` before
workspaces; its center orders temperature, memory, CPU, distro, two clocks and
idle inhibition. Its drawer click option is commented out. Hyprixe explicitly
enables native click-to-reveal, retains four workspaces, and uses an independent
Debian-compatible sensor helper. No upstream CSS, colors, Powerline separators,
Arch commands, processor paths or 10-workspace defaults are imported.

## Exact arrangement

| Zone | Modules, in order |
| --- | --- |
| Left | `group/traygroup`, `hyprland/workspaces`, `wlr/taskbar` |
| Center | `custom/temperature`, `memory`, `cpu`, `custom/distro`, `clock#time`, `clock#date`, `idle_inhibitor` |
| Right | `network`, `bluetooth`, `pulseaudio`, `battery`, `custom/power` |
| Drawer | `custom/traylauncher` remains visible; `tray`, `mpris`, `hyprland/window`, `hyprland/submap` are revealed together |

Music/title/submap modules are retained in the drawer. The per-window taskbar
stays visible after workspaces, with its original 16 px icons, click-to-focus,
active style and separate entries for multiple windows of the same app.
The bar shows only workspaces 1–4 using the native ignore-workspaces regex;
the Hyprland workspace rules and existing shortcuts for other workspaces are
unchanged. The four persistent definitions still use `*`, without an output name.

`fixed-center=true` centers the group independently of side content. Matching
minimum widths pair temperature/eye, memory/date and CPU/time so the Debian
logo itself is at the group midpoint. The original font family/weight/size,
colors, transparency, borders, rounding, margins, padding and 31 px height remain.
New module selectors reuse the original existing module declarations. The CSS
fixture regression requires every original rule to remain. The sole extra font
family/14 px size belongs to the new logo, not existing text. Narrow outputs or
very large taskbars/long expanded drawer contents still have finite available
space; verify those combinations on the real display.

## Tray and optional modules

Click **☰** to toggle the native Waybar drawer; it starts closed and uses a
200 ms reveal transition. There is no polling/toggle script or bar restart.
The tray itself has no reserved blank icon slots. Existing SNI item menus/actions
continue to be handled by Waybar. Empty music/window/submap modules hide using
their native behavior. The power action still calls Hyprixe's original
`PowerMenu.sh`, with its existing shutdown/reboot/suspend/logout choices.

The network button still opens `nm-connection-editor`; its tooltip includes
SSID/IP/interface and traffic. Bluetooth still opens `blueman-manager`.
Audio still opens `pavucontrol` on left click, toggles mute with right click,
and uses native volume scrolling. No microphone/keyboard binding changes occur.
The eye uses the native idle-inhibit protocol and explains enabled/presentation
states. Hypridle and compositor rules are not modified.

## Temperature and root storage

`waybar/scripts/temperature.py` reads discovered `hwmon*/temp*_input` files and
CPU thermal zones. Kernel CPU driver names and labels identify CPU sensors;
there is no fixed hwmon index, processor model, CPU frequency path or device name.
Core/package, AMD control/die and CPU thermal-zone data are supported. The hottest
valid recognized CPU value is displayed. GPU/NVMe/wireless/ambiguous ACPI readings
are excluded; invalid, missing, unreadable and implausible values are ignored.

When no reliable CPU reading exists, the helper reports `shutil.disk_usage('/')`.
It does not depend on a block-device name. The JSON class and tooltip identify
`temperature` or `storage`. Both unavailable yields a dash and explanatory
tooltip rather than a failing process. Discovery repeats at each five-second
update, handling sensors that appear/disappear. No lm-sensors dependency or sleep
loop is added.

Used memory is compact (`RAM 4.2G`) with total/percentage in its tooltip; CPU is
`CPU 12%`. The Debian logo is decorative and has no click action. The existing
fonts do not guarantee the private-use Debian glyph on a fresh Debian install,
so a **1,768-byte one-glyph font** is bundled. It contains only U+F306 and is
selected only for `custom/distro`; no system/global font setting is changed.

## Clocks and battery

Time is HH:MM. Date uses the session locale and weekday + day/month; a French
session yields e.g. `mar. 27/10`. No unavailable hardcoded locale can disable the
module on a fresh system. Its tooltip shows the native calendar; clicking toggles
calendar mode. If the system locale is English, weekday names remain English.

Battery uses Waybar's native Linux power-supply discovery, without `BAT0` or an
adapter name. Device-scope peripheral batteries are excluded by native Waybar.
The percentage is explicit, with charging/plugged icons, normal capacity icons,
warning at 20% and critical at 10%. Additional state colors come from the existing
Frosted Glass palette. With no battery, native Waybar hides the widget; it may
log its normal one-time `No batteries.` warning, without an error or bar failure.
Absent Bluetooth hardware is also a normal native warning, not a failed bar.

## Apply, verify and restore

```bash
cd ~/hyprixe-debian
git pull
./install.sh native --waybar-only --no-packages
systemctl --user restart waybar.service
systemctl --user status waybar.service --no-pager
./verify.sh --waybar --session
```

Use the existing UWSM-managed session. Scoped mode writes only the four Waybar
files and three font/provenance files, with dated backups under
`$XDG_STATE_HOME/hyprixe/backups/`. Custom XDG paths/spaces are supported. It
reuses existing systemd units and does not restart a session or write system
configuration. It does not require closing Dolphin or redeploy other components.
Full installation also deploys these files. `--dry-run` writes nothing.

```bash
./uninstall.sh --list
./uninstall.sh --backup WAYBAR_BACKUP_ID --dry-run
./uninstall.sh --backup WAYBAR_BACKUP_ID
systemctl --user restart waybar.service
```

Restore remains strict about later edits and preserves unrelated personal files.
No change to `graphical-session.target`, vendor `Requisite`, UWSM or the service
launcher is needed. The scoped verifier checks active source/deployed paths,
module order, four workspaces, automatic battery, helper and glyph, plus native
Lua IPC/taskbar/drawer capabilities. With `--session`, it also checks actual UWSM,
service activity and wallpaper ordering. Interactive/hardware checks are marked
SKIPPED by the portable verifier and described honestly in
[VALIDATION.md](VALIDATION.md).

Primary implementation references:
[Waybar native drawer](https://github.com/Alexays/Waybar/blob/0.12.0/src/group.cpp),
[battery discovery](https://github.com/Alexays/Waybar/blob/0.12.0/src/modules/battery.cpp),
[workspace regex filtering](https://github.com/Alexays/Waybar/blob/0.12.0/src/modules/hyprland/workspaces.cpp),
[clock/calendar](https://github.com/Alexays/Waybar/blob/0.12.0/src/modules/clock.cpp).
