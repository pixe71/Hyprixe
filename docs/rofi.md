# Shared Rofi Frosted Glass menus

[Documentation index](README.md)

`config.rasi` loads the shared fonts and `themes/Frosted-Glass.rasi`. The latter
imports `themes/Frosted-Glass-Common.rasi`, which owns the glass colours, search,
selection, row backgrounds, borders and scrollbar paint for every active menu.
`themes/Frosted-Glass-Launcher.rasi` now contains only the two-panel layout,
wallpaper and round sidebar buttons. No second copy of its CSS/Rasi is maintained.

| Entry point | Configuration | Contents/layout |
| --- | --- | --- |
| `SUPER + Space` | `config-launcher.rasi` | Native application search, wallpaper shell; Applications active |
| `ALT + F10` | `config-windows.rasi` | Existing Hyprland window snapshot, same wallpaper shell; Windows active |
| `SUPER + CTRL + V` | `config-clipboard.rasi` | Existing clipboard history, compact 42% width, eight rows, no wallpaper |
| Session action confirmation | `config.rasi` | Existing Cancel / Confirm prompt, common glass paint |
| Optional `UserScripts/RofiCalc.sh` | `config-calc.rasi` | Existing calculator layout, common glass paint; no new keybind |

The application launcher and window switcher remain centered with the same
outer radius, at 70% of output width and 58% of output height. The existing
launcher geometry is unchanged by the shared-menu update. The wallpaper box
uses 32% of output width, approximately 48% of content width; the list uses
the remaining 52%. Dimensions use
logical output percentages and font-relative button padding, including HiDPI.

The wallpaper is a Rasi `background-image` on the left box only, scaled by height
with its aspect ratio preserved. Its excess width is cropped by the box's rounded
clip. `hyprixe-preview-cover: true` requests a width-scaled image only when the
height-scaled image is narrower than the box, avoiding repetition on 32:9 outputs.
Ordinary output geometry retains the existing height crop. The same asynchronous
Rofi image cache is used; no script, delay or generated preview is involved.
No image is stretched or
copied specifically for Rofi. Deployment renders the existing wallpaper location
from `XDG_DATA_HOME`, including paths with spaces. The right panel and the area
around the image use the existing Hyprixe blue/grey palette with alpha.

## Shared colours and transparency

All active Rofi menus reuse the current application launcher's colours and alpha.
The former black background in the palette is replaced by the same blue/grey glass.
This theme reuses
Rofi `color2`, `color3`, `color11`, `color12` and the cyan border already used by
Waybar/Wlogout. Values below are opacity (alpha), not percentage transparency:

| Paint | Existing RGB | Alpha |
| --- | --- | --- |
| Main glass | `#284D5B`, Rofi color2 | 0.82 |
| Search/messages | `#345461`, Rofi color3 | 0.40 |
| Round buttons | `#345461`, Rofi color3 | 0.76 |
| Selected entry / active sidebar mode | `#457081`, Rofi color11 | 0.92 |
| Button hover | `#4D7A8A`, Rofi color12 | 0.92 |
| Subtle borders | `#7ED6FF`, Waybar/Wlogout accent | 0.20 |
| Text | `#E0F0F5`, shared Rofi foreground | 1.00 |

The mainbox, application box, unselected rows and text/icon backgrounds are
transparent. Main glass is painted once, so child containers do not compound its
opacity. The old black alternate-row background and opaque grey search field are
removed for every active menu. The search tint overlays the glass; its combined opacity
is 0.892. The selected row has 0.9856 combined opacity for legibility. The image
stays opaque. Existing Hyprland Rofi blur rules and all input actions are unchanged.

The four FontAwesome glyphs use the font already installed by Hyprixe; no icon
asset or additional font is required. Buttons use the shared background/text
colours and the existing blue/cyan selection colour on hover.

| Button | Behaviour |
| --- | --- |
| Applications | Native `drun` mode in the launcher; from the switcher, close it and call the existing `RofiLauncher.sh` |
| Files | Close Rofi, then `LaunchApp.sh dolphin` → `uwsm app -- dolphin` |
| Windows | From the launcher, close Rofi and call `WindowSwitcher.sh`; in the switcher, remain in the same view with search/PID preserved |
| Terminal | Close Rofi, then `LaunchTerminal.sh` → `uwsm app -- kitty` |

Search, desktop-entry enumeration, filtering, application icons and keyboard
navigation remain Rofi's native implementation. The original `run` and
`filebrowser` modes are still available through their existing keyboard actions;
their former text mode column is replaced visually by the four round buttons.
Keyboard focus stays in the search field, including after clicking Applications.
The clipboard keeps its existing script, search, keyboard/mouse selection,
MIME-aware decode/copy and Ctrl+Delete / Alt+Delete actions. Only its theme and
width change. The switcher still uses a single Hyprland client snapshot, returns
the original row index, validates the window address and dispatches the same
native Lua raise/focus commands. Escape and unexpected Rofi errors never focus
a window. Multiple windows of the same app remain separate class/title rows.
The sidebar's active Windows button uses an empty native Rasi action: clicking
it does not close, restart or clear the current search.

The Wlogout layout, helper and styling are unchanged. Only its existing Rofi
confirmation prompt inherits the shared paint. Historical themes/scripts under
`extras/kooldots` remain inactive and are not modified.

## Why the prepared Rofi build is required

[Rofi's native theme buttons](https://davatorium.github.io/rofi/2.0.0/rofi-theme.5/)
invoke named Rofi key actions, not arbitrary shell commands. In native `drun`,
custom actions normally select another mode rather than returning dmenu-style
exit codes. Stock 2.0.0 also does not implement custom-button hover paint.

The existing pinned Wayland build has a small local adaptation in
`scripts/rofi_launcher.py`. It is enabled only by the two wallpaper views' private
`-hyprixe-launcher` command-line switch:

- In `drun`, button actions 17–19 close the view and return fixed codes 10–12 to the caller.
  The caller maps them to the three existing helpers, without evaluating input as
  shell code. Applications remains the unmodified native action 1.
- Pointer enter/motion/leave maintain the custom buttons' hover state and their
  click coordinates. Other invocations retain the upstream pointer handling.
- The switcher uses native `dmenu`, whose sidebar action codes remain 10
  (Applications), 26 (Files) and 28 (Terminal). These are mapped to the existing
  helpers only after the view closes. It never interprets row text as a command.
- The flag is not an environment variable and cannot be inherited by desktop
  entries or commands launched by Rofi. Dolphin and Kitty use the existing UWSM
  helpers. Clipboard and confirmation dialogs keep native `dmenu` behaviour.

`build-runtime.sh` verifies the pinned upstream commit, applies exact guarded
replacements, and builds as the regular user. A mismatched source fails before
patch writes. `rofi_compat.py --launcher` checks both Wayland and this compiled
capabilities. Preview sizing is enabled by its Rasi property on the wallpaper box
only; it does not affect other images or menus. No global compositor setting,
layer rule or dependency is added.
The existing Rofi and configuration files are backed up by the normal installer
transaction and restored through the normal dated restore operation.

## Apply, verify and restore

```bash
cd ~/hyprixe-debian
git pull --ff-only
# Close Dolphin before the full deployment.
./install.sh native
./verify.sh --dependencies
./verify.sh --dependencies --session
```

If the two-panel launcher already works with the prepared Rofi, use
`./install.sh native --no-packages` to deploy the update. The full installer
remains available for fresh installs or an older incompatible Rofi. Existing
keybindings read the deployed scripts immediately; a theme-only update needs
only closing/reopening the menu. Full installation can also change shell,
SDDM or session files; follow [updating](update.md) for those changes.

`verify.sh` checks all menu imports, the existing wallpaper, four actions,
executable helpers, the three original bindings, Wayland/button capabilities and
installed XDG paths. It follows the installed import graph to reject an old
configuration that does not load the common paint or shared wallpaper shell.
Regression tests exercise native parsing/equivalent resolved styles when
available, clipboard operations, switcher dispatch, sidebar requests,
cancellation/errors, paths with spaces, idempotent deployment and restoration.

On the physical PC, check all three shortcuts, immediate typing, arrow navigation,
Enter/Escape, mouse selection, the four sidebar buttons, active-mode paint,
clipboard contents, image crop, rounded corners and blur. Headless Wayland tests
do not validate physical Hyprland GPU blur or the real window focus dispatch.

To restore, list snapshots with `./uninstall.sh --list`, then use the appropriate
snapshot as documented in [restore](uninstall-restore.md).
Restoration includes a replaced `~/.local/bin/rofi`; Debian packages installed
for compilation are not automatically removed.
