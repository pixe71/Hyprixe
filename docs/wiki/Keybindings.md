# Keybindings

`SUPER` means Windows/Meta. Default input is French AZERTY (`fr`, `latin9`).
Number-row shortcuts refer to physical key positions, not shifted symbols.

## Applications and session

| Shortcut | Action |
| --- | --- |
| `SUPER + Return` | Kitty |
| `SUPER + E` | Dolphin |
| `SUPER + Space` | Rofi application launcher |
| `SUPER + CTRL + V` | Clipboard history |
| `ALT + F10` | Graphical window switcher across workspaces |
| `SUPER + L` | Lock with Hyprlock |
| `SUPER + Backspace` / `SUPER + SHIFT + E` | Toggle the same Wlogout menu |

Wlogout offers **Lock, Logout, Shutdown and Reboot**. Exit/power actions ask for
confirmation; Logout uses UWSM. There are no Suspend/Hibernate buttons.
In clipboard history, Enter/click copies, Escape cancels, `CTRL + Delete` deletes
an entry and `ALT + Delete` clears history.

## Windows

| Shortcut | Action |
| --- | --- |
| `SUPER + Q` | Close focused window |
| `SUPER + F` | Toggle fullscreen |
| `SUPER + SHIFT + F` | Toggle maximized fullscreen mode |
| `SUPER + V` | Toggle floating |
| `SUPER + P` | Toggle pseudotiling |
| `SUPER + J` | Toggle Dwindle split direction |
| `SUPER + arrows` | Focus in that direction |
| `SUPER + SHIFT + arrows` | Move window in that direction |
| `SUPER + CTRL + arrows` | Resize by 50 logical pixels; repeats while held |
| `SUPER + left click/drag` | Move window |
| `SUPER + right click/drag` | Resize window |
| `ALT + Tab` / `ALT + SHIFT + Tab` | Cycle eligible windows on the current workspace |

Alt+Tab is a deterministic cycle, not an MRU popup. Use `ALT + F10` for a
searchable list across workspaces.

## Workspaces

| Shortcut | Action |
| --- | --- |
| `SUPER + number-row 1..0` | Select workspace 1..10 |
| `SUPER + SHIFT + number-row 1..0` | Move window to workspace 1..10 |
| `SUPER + Page Down` / mouse wheel down | Next existing workspace |
| `SUPER + Page Up` / mouse wheel up | Previous existing workspace |
| Three-finger horizontal swipe | Workspace gesture |

Only **1–4 are persistent and shown in Waybar**. Workspaces 5–10 remain available.
The last number-row position selects workspace 10.

## Screenshots

| Shortcut | Capture | Destination |
| --- | --- | --- |
| `SUPER + SHIFT + S` | Area | Clipboard |
| `Print` | Full desktop | `~/Pictures/Screenshots/` |
| `SHIFT + Print` | Area | `~/Pictures/Screenshots/` |
| `SUPER + Print` | Full desktop | File and clipboard |
| `SUPER + SHIFT + Print` | Area | File and clipboard |

The file-and-clipboard variants follow the XDG Pictures directory. Cancelling
area selection does not take a different screenshot.

## Media and brightness

| Key | Action |
| --- | --- |
| Volume up/down | Default PipeWire output ±5%, increase capped at 100% |
| Audio mute / microphone mute | Toggle output / input mute |
| Play / Next / Previous | playerctl play-pause / next / previous |
| Brightness up/down | brightnessctl ±5% |

Hardware must expose the corresponding keys and controls. Media/audio bindings
also work while locked.

The canonical configuration is `common/config/hypr/lua/keybinds.lua`; personal
replacements belong in `UserConfigs/user_keybinds.lua`. Disable the existing
`KOOLDOTS_BINDS["CHORD"]` handle before adding a replacement. See [Customization](Customization).
