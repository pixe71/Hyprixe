# Rofi application launcher

Only `SUPER + Space` uses `hypr/rofi/config-launcher.rasi`. It imports the unchanged
`config.rasi`, shared fonts, Frosted Glass theme and palette, then adds
`themes/Frosted-Glass-Launcher.rasi`. The window remains centered with the same
outer radius, at 70% of output width and 58% of output height. This is 16.7%
wider than the previous 60% layout, with no height increase. The wallpaper box
uses 32% of output width, approximately 48% of content width; applications use
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

## Launcher-only colours and transparency

The shared Rofi palette and other dialogs are unchanged. This extension reuses
Rofi `color2`, `color3`, `color11`, `color12` and the cyan border already used by
Waybar/Wlogout. Values below are opacity (alpha), not percentage transparency:

| Paint | Existing RGB | Alpha |
| --- | --- | --- |
| Main glass | `#284D5B`, Rofi color2 | 0.82 |
| Search/messages | `#345461`, Rofi color3 | 0.40 |
| Round buttons | `#345461`, Rofi color3 | 0.76 |
| Selected application | `#457081`, Rofi color11 | 0.92 |
| Button hover | `#4D7A8A`, Rofi color12 | 0.92 |
| Subtle borders | `#7ED6FF`, Waybar/Wlogout accent | 0.20 |
| Text | `#E0F0F5`, shared Rofi foreground | 1.00 |

The mainbox, application box, unselected rows and text/icon backgrounds are
transparent. Main glass is painted once, so child containers do not compound its
opacity. The old black alternate-row background and opaque grey search field are
overridden only here. The search tint overlays the glass; its combined opacity
is 0.892. The selected row has 0.9856 combined opacity for legibility. The image
stays opaque. Existing Hyprland Rofi blur rules and all input actions are unchanged.

The four FontAwesome glyphs use the font already installed by Hyprixe; no icon
asset or additional font is required. Buttons use the shared background/text
colours and the existing blue/cyan selection colour on hover.

| Button | Behaviour |
| --- | --- |
| Applications | Native `drun` mode, in the same Rofi process; no second launcher |
| Files | Close Rofi, then `LaunchApp.sh dolphin` → `uwsm app -- dolphin` |
| Windows | Close Rofi, then the existing `WindowSwitcher.sh`, unchanged |
| Terminal | Close Rofi, then `LaunchTerminal.sh` → `uwsm app -- kitty` |

Search, desktop-entry enumeration, filtering, application icons and keyboard
navigation remain Rofi's native implementation. The original `run` and
`filebrowser` modes are still available through their existing keyboard actions;
their former text mode column is replaced visually by the four round buttons.
Keyboard focus stays in the search field, including after clicking Applications.
Other Rofi dialogs keep their original theme and layout.

## Why the prepared Rofi build is required

[Rofi's native theme buttons](https://davatorium.github.io/rofi/2.0.0/rofi-theme.5/)
invoke named Rofi key actions, not arbitrary shell commands. In native `drun`,
custom actions normally select another mode rather than returning dmenu-style
exit codes. Stock 2.0.0 also does not implement custom-button hover paint.

The existing pinned Wayland build therefore has a small local adaptation in
`scripts/rofi_launcher.py`. It is enabled only by the launcher's private
`-hyprixe-launcher` command-line switch:

- Button actions 17–19 close the view and return fixed codes 10–12 to the caller.
  The caller maps them to the three existing helpers, without evaluating input as
  shell code. Applications remains the unmodified native action 1.
- Pointer enter/motion/leave maintain the custom buttons' hover state and their
  click coordinates. Other invocations retain the upstream pointer handling.
- The flag is not an environment variable and cannot be inherited by desktop
  entries or commands launched by Rofi. It is not passed to Dolphin, Kitty or the
  switcher. Regular `dmenu`, power and Wlogout confirmation dialogs keep their
  upstream custom-action behaviour.

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
git pull
./install.sh native
./verify.sh --dependencies
./verify.sh --dependencies --session
```

The glass update also requires the preview rendering capability. The normal
installer rebuilds an older prepared Rofi when necessary; `--no-packages` skips
that preparation and correctly refuses an incompatible existing binary. The
unchanged `SUPER + Space` binding reads the deployed script immediately.

`verify.sh` checks the dedicated imports, existing wallpaper, four actions,
executable helpers, original binding, Wayland/button capabilities and installed
XDG paths. Regression tests exercise native theme parsing when available, fixed
action dispatch, cancellation/errors, paths with spaces, idempotent deployment
and restoration of the previous launcher and its original file mode.

On the physical PC, check typing immediately after opening, arrow navigation,
Enter/Escape, the four mouse actions, hover/leave colours, image crop, rounded
corners and blur. Automated checks do not claim to validate physical GPU blur.

To restore, list snapshots with `./uninstall.sh --list`, then use the appropriate
snapshot as documented in [INSTALL.md](../INSTALL.md#restore--uninstall).
Restoration includes a replaced `~/.local/bin/rofi`; Debian packages installed
for compilation are not automatically removed.
