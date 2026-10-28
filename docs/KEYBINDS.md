# Native keyboard and mouse audit

## Scope and evidence

The native load graph contains one shipped binding source:
`hyprland.lua` loads `lua/keybinds.lua`, then
`UserConfigs/user_keybinds.lua` (currently comments only), then startup hooks.
No `extras/` configuration is loaded. There are **67 bindings**, no active
unbind, and no duplicate chord in the shipped graph. Native and VMware profiles
use the same bindings. Four compositor-persistent workspaces remain unchanged.

The API was inspected in the exact upstream **v0.55.2 and v0.56.2** sources.
The real Debian backports Hyprland **0.55.2** binary also loaded the complete
configuration using `--verify-config` in a temporary HOME with spaces. Additional
assertions read all 67 native `HL.Keybind` objects and construct every dispatcher
variant used here. They passed. This is stronger than the recording Lua mock;
it still is **not a running compositor or a physical input test**.

Starting an isolated compositor in this Windows/WSL environment failed at
backend creation (no DRM/GPU device). No `hyprctl binds` result from the user's
physical Debian session has been collected here. In particular, the reported
Alt+Tab / reverse / F10 failures are **not yet assigned a proven physical cause**.
Do not infer that they were fixed solely from a successful parser test.

## Findings and targeted changes

| Finding | Change / interpretation |
| --- | --- |
| `cycle_next` iterates window/z-order; the following `alter_zorder(top)` mutates that same order | Replace this combination with one native Lua `get_windows` snapshot, sorted by immutable `stable_id`. Next/previous are inverses regardless of raising. Keep raising floating windows, then focus the explicit address. |
| `hl.dsp.focus({window="address:0x..."})` is the Lua IPC focus expression | Keep it in the Rofi switcher; raise the explicit selected address first so an overlapping floating window can become visible. Do not revert to legacy syntax. |
| `hl.bind` does not read `opts.mouse` | Remove the ignored option. Interactive mouse bindings use `window.drag()` / `window.resize()` with no pixel arguments. `mouse:false` in IPC is normal for these Lua callbacks, not evidence they are keyboard binds. |
| The previous mock asserted the ignored mouse option | Assert the actual drag/interactive-resize dispatchers instead. |
| Window switcher could use a distribution Rofi ahead of the managed binary | Prepend `~/.local/bin`, matching the session and installer. Check the required commands and Rofi config. Whether a stale PATH caused the reported F10 failure is not yet proven. |
| `hyprctl` may return a Lua error with exit status zero | Require the exact `ok` response after focus. Report abnormal Rofi exit codes rather than treating every failure as cancellation. |
| `hyprctl -j binds` exposes Lua callbacks as `__lua` with an opaque registry number | Add stable `Hyprixe | <chord>` descriptions. No action or modifier is changed by this metadata. |
| JSON does not expose `enabled`; Lua `code:N` rows can have empty `key` and zero `keycode` | Also inspect retained `HL.Keybind` handles through read-only `hyprctl eval`, including `is_enabled()`, `display_key`, modifiers, submap and device/consumption filters. Detect later disable/unbind. |

The switcher takes **one** client snapshot, filters hidden/unmapped clients,
uses a numeric Rofi selection, validates the selected hex address, and focuses
that individual window. Multiple windows of the same application remain separate
entries. Direct execution of this short-lived Rofi menu retains the inherited
UWSM session environment and its stdout selection. Application launchers keep
their existing `uwsm app --` commands.

The old cycle defect follows directly from the upstream implementation and is
covered by a three-window regression that mutates z-order on every selection.
For example, starting at A in `[A,B,C]`, the old forward step selects B and raises
it, leaving `[A,C,B]`; the next step wraps to A and can keep skipping C. This is a
confirmed algorithmic defect, distinct from a physical shortcut that never fires.
The replacement uses only native Lua queries/dispatchers (no shell process,
cached IPC file, timer or daemon). It honors the active special workspace, ignores
hidden/non-input windows, permits fullscreen-blocked candidates when cycling from
fullscreen, and handles empty/one-window workspaces and closures without an index
cache. The order is stable creation-ID order, not an MRU popup. Alt+F10 keeps the
graphical selector across workspaces.

## Complete shortcut contract

| Shortcut | Action |
| --- | --- |
| SUPER + Return | Kitty through UWSM |
| SUPER + Backspace | Toggle Wlogout: Lock, Logout, Shutdown, Reboot |
| SUPER + E | Dolphin through UWSM |
| SUPER + Space | Frosted Glass Rofi launcher through UWSM |
| SUPER + Q | Close active window |
| SUPER + L | Hyprlock through UWSM, with duplicate guard |
| SUPER + V | Toggle floating |
| SUPER + F / SUPER + SHIFT + F | Fullscreen / maximize |
| SUPER + P / SUPER + J | Toggle pseudo / dwindle split |
| SUPER + left mouse button (272) | Interactive move |
| SUPER + right mouse button (273) | Interactive resize |
| SUPER + arrow | Focus in that direction |
| SUPER + SHIFT + arrow | Move window in that direction |
| SUPER + CTRL + arrow | Resize by 50 px; repeats while held |
| SUPER + top-row positions 1–0, XKB codes 10–19 | Workspaces 1–10; 1–4 persistent, 5–10 dynamic |
| SUPER + SHIFT + those positions | Move window to workspace 1–10 |
| SUPER + PageUp / wheel up | Previous existing workspace |
| SUPER + PageDown / wheel down | Next existing workspace |
| ALT + Tab / ALT + SHIFT + Tab | Next / previous window on current workspace |
| ALT + F10 | Rofi switcher across workspaces; select with Enter |
| SUPER + CTRL + V | Clipboard history |
| SUPER + SHIFT + E | Session/power menu |
| SUPER + SHIFT + S | Select screenshot area and copy PNG |
| Print / SHIFT + Print | Save full desktop / selected area to `~/Pictures/Screenshots/` |
| SUPER + Print / SUPER + SHIFT + Print | Existing full/area screenshot, save and copy |
| Volume up/down / speaker mute / microphone mute | PipeWire volume/mute; enabled while locked; volume repeats |
| Play / Next / Previous | Player control; enabled while locked |
| Brightness up/down | Brightness control; repeats while held |

Use the physical **left Alt** (MOD1, mask 8); French AltGr is normally MOD5,
not the requested Alt modifier. SHIFT is 1, CTRL is 4, SUPER is 64.
Workspace codes are **XKB keycodes**, including the evdev +8 offset; they work
on the shipped French AZERTY layout without binding the shifted digit symbols.
Keysym bindings retain the existing layout behavior. An alternate keymap,
per-device binding policy, active submap or application shortcut inhibitor may
affect input delivery; the audit does not disable these policies automatically.

## Apply and audit the actual session

After retrieving these changes, run as the desktop user inside Hyprland:

```bash
cd ~/hyprixe-debian
./install.sh native --no-packages
hyprctl reload
hyprctl configerrors
./verify.sh --dependencies --session
```

Use `./install.sh native` if dependencies need installation. If the compositor
PATH or UWSM environment is stale, save work, log out and choose
**Hyprland (uwsm-managed)** in SDDM again.

When the Hyprland binary is available and the verifier runs unprivileged,
the default checks also run its real `--verify-config` parser against a private
temporary copy of the native configuration, retained-handle assertions and
dispatcher constructors. The existing desktop's IPC/display/bus environment is
excluded. No compositor backend or startup hook is run. Missing binaries or a
root invocation make this additional check **SKIPPED**; it is not a session test.

`--session` now compares the actual registry against all 67 expected bindings,
including modifiers, flags, submaps and obvious duplicate triggers (also personal
bindings). It reports missing audit identities, removed callback references,
disabled handles, opaque unlabelled physical binds that cannot be checked for
conflicts, script permission/path problems, installed-file drift, missing command
dependencies, and incompatible Rofi. It queries live keyboard/keymap information.
Version/constructor failures are explicit. Live read-only queries also validate
the snapshot API, window IDs, addresses and visibility/input fields.
Constructor probes execute **only
`no_op`**, never window close/move/focus, screenshots, locking or power actions.
The address selector in that probe is a constructor-only sentinel, not a window
to be focused. Registry/API success does not prove callback effects or input.
The audit reads `configerrors` first and skips Lua probes when errors exist:
upstream evaluation clears the stored error list, so querying it afterwards
would risk hiding an existing load failure.

If an Alt shortcut remains inactive, capture evidence from the affected session:

```bash
./verify.sh --session --diagnostics > "$HOME/hyprixe-keybind-audit.txt" 2>&1
hyprctl -j binds
hyprctl -j devices
hyprctl submap
# Separate script/UI problems from physical binding delivery:
"${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/WindowSwitcher.sh"
```

The diagnostic report includes keybind identities, keymaps and relevant input
options; it omits bind command arguments. The direct script opens the real
switcher, and Enter intentionally focuses the selected window. If it works while
F10 does not, investigate the loaded chord, active submap and actual key events.
An input-event viewer such as `wev`, if installed, can identify the physical
Alt/Tab/F10 keys and modifiers; the verifier does not install or launch one.

Manual validation must use at least two ordinary windows on the **same** workspace
for cycling, then windows on different workspaces for the graphical switcher.
Test both directions repeatedly, floating windows, mouse press/move/release,
AZERTY top-row workspace moves, screenshots and clipboard pasting. These checks
remain required on the physical Hyprland 0.56.2 PC.

## Primary implementation references

- [v0.56.2 bind parsing/options](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsToplevel.cpp)
- [v0.56.2 retained keybind properties](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/objects/LuaKeybind.cpp)
- [v0.56.2 dispatchers](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsDispatchers.cpp)
- [v0.56.2 IPC representation](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/debug/HyprCtl.cpp)
- [v0.55.2 dispatchers](https://github.com/hyprwm/Hyprland/blob/v0.55.2/src/config/lua/bindings/LuaBindingsDispatchers.cpp)
- [v0.56.2 cycle ordering](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/desktop/state/WindowQuery.cpp)
- [v0.56.2 z-order mutation](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/desktop/state/WindowState.cpp)
- [v0.56.2 native window queries](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsQuery.cpp)
- [v0.56.2 window properties](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/objects/LuaWindow.cpp)
