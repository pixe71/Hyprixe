# Keybindings

[Documentation index](README.md)

The active source is [lua/keybinds.lua](../common/config/hypr/lua/keybinds.lua), loaded
by [hyprland.lua](../common/config/hypr/hyprland.lua). The current configuration defines
**68 keyboard/mouse bindings** plus a workspace gesture. The
[personal override file](../common/config/hypr/UserConfigs/user_keybinds.lua) loads
afterwards and currently adds no bindings. Optional KoolDots examples are not
part of this load graph.

`SUPER` is the Windows/Meta key. Default input is French AZERTY (`fr`, `latin9`).
Number-row shortcuts use XKB keycodes 10–19, not shifted AZERTY symbols: these
are the physical positions labelled 1–0 on a QWERTY keyboard. `1..4` below means
those first four positions; the last position selects workspace 10.

## Applications and menus

| Shortcut | Action |
| --- | --- |
| `SUPER + Return` | Kitty through `LaunchTerminal.sh` and `uwsm app -- kitty` |
| `SUPER + E` | Dolphin through the UWSM application helper |
| `SUPER + Space` | Rofi applications, wallpaper/sidebar shell |
| `SUPER + CTRL + V` | Compact Rofi clipboard history |
| `ALT + F10` | Rofi window switcher with the same wallpaper shell |

Clipboard: Enter/click selects and copies, Escape cancels, `CTRL + Delete`
deletes an entry and `ALT + Delete` clears history. These are menu-local keys,
not additional compositor bindings. See [Rofi](rofi.md).

## Window management

| Shortcut | Action |
| --- | --- |
| `SUPER + Q` | Close focused window |
| `SUPER + F` | Toggle fullscreen |
| `SUPER + SHIFT + F` | Toggle maximized fullscreen mode |
| `SUPER + V` | Toggle floating |
| `SUPER + P` | Toggle pseudotiling |
| `SUPER + J` | Dwindle split direction toggle |
| `SUPER + arrows` | Focus in that direction |
| `SUPER + SHIFT + arrows` | Move window in that direction |
| `SUPER + CTRL + arrows` | Resize by 50 logical pixels; repeats while held |
| `SUPER + left click/drag` | Move window, native Lua drag dispatcher |
| `SUPER + right click/drag` | Resize window, native Lua resize dispatcher |

Mouse buttons use `mouse:272` and `mouse:273`. Lua drag/resize dispatchers are
used directly; the legacy `opts.mouse` flag is not required. A false `mouse`
field in bind IPC alone does not mean these callbacks are invalid.

## Workspaces

| Shortcut | Action |
| --- | --- |
| `SUPER + number-row 1..0` | Focus workspace 1..10 |
| `SUPER + SHIFT + number-row 1..0` | Move focused window to workspace 1..10 |
| `SUPER + Page Down` / mouse wheel down | Next existing workspace |
| `SUPER + Page Up` / mouse wheel up | Previous existing workspace |
| Three-finger horizontal touchpad swipe | Workspace gesture |

Only **1–4 are persistent** in Hyprland and always shown by Waybar. Binds for
5–10 remain available; Waybar intentionally filters them out. No output name is
hardcoded by the persistence rules. See [Waybar](waybar.md).

## Window switching

| Shortcut | Action |
| --- | --- |
| `ALT + Tab` | Next eligible window on the current workspace |
| `ALT + SHIFT + Tab` | Previous eligible window on the current workspace |
| `ALT + F10` | Search mapped, visible windows across workspaces |

Alt+Tab takes one native Lua window snapshot, sorts stable IDs, raises and
focuses the selected address. It uses the active special workspace when one is
open. It is a deterministic cycle, not an MRU popup or a modifier-release menu.
The graphical switcher distinguishes window titles, validates the selected
address and does nothing when cancelled or when Rofi fails.

## Session and lock

| Shortcut | Action |
| --- | --- |
| `SUPER + L` | Hyprlock through the duplicate-protected lock helper |
| `SUPER + Backspace` | Toggle the Wlogout session menu |
| `SUPER + SHIFT + E` | Toggle the same Wlogout menu, through the same helper |

Wlogout contains exactly Lock, Logout, Shutdown and Reboot. Logout uses
`uwsm stop` after confirmation. No Suspend or Hibernate action is supplied.
See [Wlogout](wlogout.md) and [locking/idle](hyprlock-hypridle.md).

## Screenshots

| Shortcut | Capture | Destination |
| --- | --- | --- |
| `SUPER + SHIFT + S` | Select area with slurp | Clipboard only |
| `Print` | Full desktop | `~/Pictures/Screenshots/` |
| `SHIFT + Print` | Select area | `~/Pictures/Screenshots/` |
| `SUPER + Print` | Full desktop | File and clipboard |
| `SUPER + SHIFT + Print` | Select area | File and clipboard |

[ScreenShot.sh](../common/config/hypr/scripts/ScreenShot.sh) uses grim/wl-copy, creates
the destination and uses timestamped, collision-safe filenames. The two legacy
file-and-clipboard modes follow the XDG Pictures directory; plain Print and
Shift+Print use the explicitly requested HOME Pictures path. Cancelling area
selection does not capture another region.

## Media and brightness

| Key | Action |
| --- | --- |
| Volume up/down | PipeWire default sink ±5%, capped at 100% on increase |
| Audio mute | Toggle default sink mute |
| Microphone mute | Toggle default source mute |
| Play / Next / Previous | playerctl play-pause / next / previous |
| Brightness up/down | brightnessctl ±5% |

Audio/media bindings are allowed while locked; volume and brightness steps
repeat. Availability depends on the keyboard exposing those XF86 keys and on
the corresponding hardware/services.

## Audit and customization

```bash
hyprctl -j binds
hyprctl configerrors
./verify.sh --dependencies --session
```

The live verifier compares loaded callbacks/retained handles and descriptions
with the expected contract, including enabled state and modifier conflicts.
It checks API constructors without dispatching destructive actions. It does
not prove that a physical key, mouse drag, screenshot or PAM unlock worked.

For a replacement in the repository's personal override file, disable the
existing `KOOLDOTS_BINDS["CHORD"]` handle before adding a new `hl.bind`.
Deploy and reload, then rerun the live audit. See [customization](customization.md).
