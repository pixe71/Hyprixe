# Dolphin: original interface, neutral light Frosted Glass paint

Target tested: Debian 13 Dolphin 25.04.3, Qt 6.8.2, KF6 6.13 and Kvantum 1.1.4.

## Interface restoration

Commit `9259fa5` introduced unwanted UI changes: forced 96 px icons, global icon
view, a narrow locked right column with Places above Information, new navigation
buttons, hidden Folders/Terminal, changed metadata filters and view properties.
Those changes are removed. Repository `dolphinrc` and `dolphinui.rc` match parent
`5d87b34` byte for byte, checked against `dolphin/interface-baseline.json`.
The generated dock preset, global `.directory`, Baloo filter preset and layout
generator are removed. No replacement layout is introduced.

The PC's actual old panel positions are runtime state, not recoverable from Git
alone. `--restore-dolphin-interface` therefore uses the original dated installer
backup. It selects the earliest intact deployment whose installed toolbar hash
matches the rejected release and whose original toolbar differs. An explicit
backup ID can also be selected. The restoration includes only entries from:

- `$XDG_CONFIG_HOME/dolphinrc` and `baloofileinformationrc`;
- `$XDG_DATA_HOME/kxmlgui5/dolphin/dolphinui.rc`;
- `$XDG_DATA_HOME/dolphin/view_properties/global/.directory` and its directory's
  exact `user.kde.fm.viewproperties#1` attribute;
- `$XDG_STATE_HOME/dolphinstaterc`;
- the previous Places/Devices/RemovableDevices visibility flags, when recorded,
  while retaining current bookmarks and other group settings.

No other files from a full-desktop backup are restored. Current interface files
are saved in a new `*-native-dolphin-interface` transaction first. A private
state marker prevents later repetitions from reverting personal adjustments.
Missing/corrupt backups stop the operation clearly; another layout is never
guessed. The restore does not require Git history on the installed machine.

## Apply

Close Dolphin normally and finish file operations first. The installer refuses
to modify configuration while Dolphin runs; it never kills it.

```bash
cd ~/hyprixe-debian
git pull
./install.sh native --dolphin-only
./verify.sh --dolphin
uwsm app -- dolphin
./verify.sh --dolphin --session
```

The current palette update uses only `--dolphin-only` and preserves the accepted
interface. The separate `--restore-dolphin-interface` flag is reserved for
recovering the rejected legacy layout from a backup. Add `--dry-run` for
a preview; missing dependencies are checked before configuration writes. Use
`--interface-backup=ID` with both restoration flags to select a matching backup
from `./uninstall.sh --list` explicitly.

## Paint and transparency

| Paint | Color | SVG alpha / opacity |
| --- | --- | --- |
| Main window | `#e7e9e8` | 78% |
| Dock interior | `#d5d9d8` | 38% over the existing window, where Qt draws dock interiors |
| Menubar interior | `#dde1df` | 40% |
| Menus | `#e8ebe9` | 94% |
| Tooltips | `#edf0ee` | 96% |
| Selection | `#c4dce2` | 88% |
| Focus/hover accent | `#cadbdd` | 24% focus wash |
| Main text | `#2d3437` | opaque before compositor opacity |
| Secondary/disabled text | `#697477` | opaque before compositor opacity |
| Links | `#528a98` | opaque before compositor opacity |

The palette uses neutral off-white glass, pale gray panels and dark text, with
small cyan accents. Every SVG opacity and the existing blur/transparency settings
are identical to the previously accepted blue variant (`0a92888`). The variant changes
paint and text colors only: SVG paths, dimensions, margins, icon metrics and
widget geometry remain identical to the original theme. Dock interiors apply
where requested by Qt; the theme does not insert extra panels or overlays.
`transparent_dolphin_view=true` removes the opaque view background;
`composite=true` and `translucent_windows=true` let Kvantum create translucent
Qt surfaces. A translucent SVG is essential: the old white SVG was opaque despite
those flags. `reduce_window_opacity` remains zero; this is alpha in the surface,
not a new global window-opacity workaround.

Dolphin's KDE color manager can reapply a light palette after Kvantum startup.
The matching KDE scheme is therefore selected through Dolphin's own
`[UiSettings] ColorScheme=Hyprixe Frosted Dolphin`. This is the only style key
merged into its preferences; no layout setting is changed. Other Qt apps keep
their existing global theme. The installed color scheme is available in KDE's
color menu but is not selected globally.

No Hyprland rule is added. Existing native blur is enabled (size 4, three passes)
and rounds windows to 13 px; existing active/inactive opacity remains 0.78/0.72.
Kvantum's blur flags are retained, but they do not replace compositor blur.
Transparency and text opacity also depend on these pre-existing Hyprland values.

## Files deployed by the paint-only installer

| Source | Destination |
| --- | --- |
| `.config/Kvantum/Frosted-Glass-Dolphin/*` | `$XDG_CONFIG_HOME/Kvantum/Frosted-Glass-Dolphin/` |
| Dolphin association merged into `Kvantum/kvantum.kvconfig` | `$XDG_CONFIG_HOME/Kvantum/kvantum.kvconfig` |
| `.local/share/color-schemes/HyprixeFrostedDolphin.colors` | `$XDG_DATA_HOME/color-schemes/HyprixeFrostedDolphin.colors` |
| Only Dolphin's `UiSettings/ColorScheme` | `$XDG_CONFIG_HOME/dolphinrc` |

These are five files with dated private backups. The shared Kvantum master keeps
its existing global theme and other application associations. An existing
explicit Dolphin association is replaced without removing its other apps.
Normal full installation preserves existing Dolphin interface files; fresh
installs seed the restored original interface plus the color selection.
Custom XDG roots and spaces are supported. No system theme/session file is
written by the component installer. Sudo is used only if APT needs to install
missing packages. `kio-extras` and `udisks2` remain useful preview/device runtime
dependencies; Breeze Dark icons stay unchanged.

`tools/build-dolphin-theme.py` reproducibly derives the variant from the original
Frosted-Glass pair. It is a maintainer tool, not a startup program. Original
SVG/config and wallpaper hashes remain unchanged. Credits remain Vince/Liuice,
KvAdapta/Tsu Jan, Senshi and the inherited KoolDots integration.

## Restore

Close Dolphin, then choose the transaction printed during installation:

```bash
./uninstall.sh --list
./uninstall.sh --backup PAINT_BACKUP_ID --dry-run
./uninstall.sh --backup PAINT_BACKUP_ID
```

The `*-native-dolphin` paint transaction restores the prior theme association and
color selection. If Dolphin has since saved other preferences, restoration
merges only the old `ColorScheme` key back and retains those interface changes.
A conflicting manual color-scheme or shared Kvantum edit blocks restoration;
no silent overwrite occurs. The separate `*-native-dolphin-interface` transaction
can undo the one-off interface rollback if explicitly requested. Do not restore
an entire old full-desktop transaction just to recover Dolphin.

Legacy backups retain strict conflict checking; `--save-dolphin-changes` can
preserve their changed managed Dolphin files and exact view xattr before restoring
originals. It does not authorize overwriting another application's settings.
Backups are under `$XDG_STATE_HOME/hyprixe/backups/`, normally
`~/.local/state/hyprixe/backups/`.

## Verification and limits

`./verify.sh --dolphin` checks source interface hashes, KConfig/XML, actual
translucent SVG paints, the app association and installed color selection,
Dolphin Qt6 linkage, Kvantum and thumbnail plugins. Optional PyQt6 instantiates
the real Kvantum style and its Dolphin theme palette; without the bindings that
probe is SKIPPED. It never treats a particular dock layout or icon size as a
validation requirement. `--dolphin --session` additionally checks UWSM services,
the manager's `QT_STYLE_OVERRIDE=kvantum`, the live compositor blur option and
running Dolphin processes' style override. It prints no process environment.

Actual GUI validation and its limits are recorded in [VALIDATION.md](VALIDATION.md).
The isolated Wayland test can demonstrate an alpha surface and wallpaper showing
through it. It cannot validate the user's physical Hyprland blur, monitor scaling
or interactive mouse/keyboard experience. On the PC, confirm unchanged panels,
view and buttons, readable text/selection, context menus, and blur over the forest.

Primary references:
[Kvantum theme configuration](https://github.com/tsujan/Kvantum/blob/master/Kvantum/doc/Theme-Config),
[Kvantum per-application theme selection](https://github.com/tsujan/Kvantum/blob/master/Kvantum/style/Kvantum.cpp),
[KDE per-application palette selection](https://github.com/KDE/kcolorscheme/blob/v6.13.0/src/kcolorschememanager.cpp).
