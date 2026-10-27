# Dolphin: minimal Frosted Glass layout

Target: Debian 13 Dolphin **25.04.3**, KDE Frameworks 6.13, Qt **6.8.2**.
The reference screenshot mentioned in the request is not attached to this
conversation context. The layout implements the requested arrangement; no
pixel-identical comparison with that screenshot is claimed.

## Result

- Main area: icon mode, **96 logical-pixel** icons/previews, wider item cells,
  up to two text lines, folders first, no extra metadata columns.
- Right column: **Places above Information**, initially 264 logical pixels wide.
  Devices/removable devices are normal groups inside Places, not separate docks.
  A group with no devices may be absent. Long bookmark/device lists scroll.
- Large selected-item preview/icon with Type, Size and Modified information.
  Hover does not replace the selection preview. Tag/rating/comment editors and
  noisy duplicate metadata fields are hidden; file contents/tags are not deleted.
- Back, Forward, Up, compact breadcrumb/location navigator, Search and menu.
  Icon-only buttons; no classic menu/status bar, Folders tree or terminal panel.
- Existing **Breeze Dark** folder icons and **Kvantum Frosted-Glass**. No new
  icon theme, global palette or Fusion fallback is introduced. The original
  Kvantum SVG/config and all Hyprland opacity/blur/rounding values are unchanged.

The breadcrumb and hamburger menu retain navigation/settings access. Ctrl+1
selects icon mode, Ctrl+M toggles the menu, F9 toggles Places and F11 Information.
Panels can be unlocked in their context menu and resized using the splitter.
Windows/tabs, terminal integration and Dolphin's ordinary actions remain usable.

## Apply only Dolphin

Close Dolphin normally and finish any file operation before installing. The
installer refuses to write while a Dolphin process belonging to the user is
running; it never kills the process.

Run inside the existing Hyprland/UWSM session:

```bash
cd ~/hyprixe-debian
git pull
./install.sh native --dolphin-only
./verify.sh --dolphin
uwsm app -- dolphin
```

Missing Qt 6 Dolphin/Kvantum, thumbnail and device dependencies are prepared from
Debian stable using sudo only for APT. If already available, no sudo/APT is used.
`--no-packages` fails clearly instead of installing dependencies. `--dry-run`
previews changes without writing configuration/backups. A normal full install
also deploys these settings; `--dolphin-only` applies the same shared Dolphin
configuration without switching native/VMware profiles or redeploying the desktop.

An identical repeat is a no-op before Dolphin writes further state. Reapplying
after Dolphin changes its preferences/window state can create another backup;
this deliberately preserves the intervening configuration.

## Files and native behavior

| Repository file | Installed destination / purpose |
| --- | --- |
| `.config/dolphinrc` | `$XDG_CONFIG_HOME/dolphinrc`: icon sizing, global view policy, toolbar style, hidden menu/status, panel lock/previews |
| `.config/baloofileinformationrc` | `$XDG_CONFIG_HOME/baloofileinformationrc`: managed metadata visibility, merged with other preferences |
| `.local/share/kxmlgui5/dolphin/dolphinui.rc` | `$XDG_DATA_HOME/kxmlgui5/dolphin/dolphinui.rc`: toolbar actions; KF6 still uses this path |
| `.local/share/dolphin/view_properties/global/.directory` | Initial global icon/preview/sorting properties |
| `dolphin/dock-layout.ini` | `[State] State` merged into `$XDG_STATE_HOME/dolphinstaterc`; preserves other entries, including window sizes |
| `tools/generate-dolphin-layout.py` | Optional maintainer tool using real Qt 6 `QMainWindow.saveState(0)`; not installed/run at login |
| `packages-dolphin.txt` | Component dependencies, also present in the normal package manifest |

Default XDG roots are `~/.config`, `~/.local/share`, `~/.local/state`; custom roots
and spaces are supported. There is no username, monitor name, mount point,
device UUID, maximized-screen flag or saved VM window placement in the preset.
Its reference widget size is used to compute the dock split, not to force the
application's window geometry. Qt adapts the layout to the actual window and DPI.

Three compatibility details matter:

1. Dolphin 25.04's status setting is the enum **`Disabled`**, not boolean `false`.
   Its dock state is stored separately in **`dolphinstaterc [State]`**. Updating
   only `dolphinrc` cannot reliably place/show the panels.
2. Baloo Widgets initializes its metadata filter at schema version **13** and
   resets the Show group if the marker is missing. The preset includes the
   native blacklist, marker and the requested additional hiding. A newer existing
   marker is retained. Native default-true entries may disappear when KDE saves.
3. Dolphin can migrate global `.directory` properties to
   **`user.kde.fm.viewproperties#1` on its containing directory**. Default fields
   or both storage forms can disappear when the view uses native defaults.
   The verifier checks effective values and rejects an explicit Details-mode
   override; it does not recreate a legacy file merely to satisfy a test.

The installer snapshots that one view-property xattr for restoration. Other
xattrs are not changed. Existing `user-places.xbel` bookmarks are retained; only
the Places/Devices/RemovableDevices group-hidden flags are set false. No bookmark
file or device entry is invented on a fresh installation: KDE generates its
usual locations. Other groups retain their existing visibility. This is KDE's
shared Places metadata, so those three group visibility flags can also affect
KDE file dialogs; no other application's layout/style is changed.

`kio-extras` provides the Qt 6 thumbnail worker and JPEG/image creators;
`kdegraphics-thumbnailers` alone does not provide them. `udisks2` supplies the
Solid device backend. Existing preview plugin selections, including video and
Windows-format thumbnails, are retained.

## Restore the previous layout

Close Dolphin, select the dated `*-native-dolphin` backup printed at install:

```bash
./uninstall.sh --list
./uninstall.sh --backup ID_FROM_LIST --dry-run --save-dolphin-changes
./uninstall.sh --backup ID_FROM_LIST --save-dolphin-changes
uwsm app -- dolphin
```

Backups live under `$XDG_STATE_HOME/hyprixe/backups/` and are private. Ordinary
restore still refuses any file edited since deployment. Dolphin normally writes
its preferences/state itself, so the explicit `--save-dolphin-changes` option
preserves changed **managed Dolphin files and its view xattr** in
`BACKUP/preserved-dolphin-…/` with a manifest before restoring their originals.
Unrelated-file conflicts and corrupt backups still block the operation before
any restoration. The option never authorizes overwriting another application's
edits. Newly created personal files/bookmarks outside the transaction remain.
When no previous Dolphin configuration existed, only the installed managed files
and newly introduced view xattr are removed. Old backups without the new metadata
records retain their existing strict restore behavior.

## Validation and limits

`./verify.sh --dolphin` checks source/deployed KConfig and XML, toolbar actions,
effective global view properties (file/xattr/defaults), dock-state format, metadata
visibility, Qt 6 linkage, Kvantum plugin/config, conflicting `QT_STYLE_OVERRIDE`,
thumbnail plugins and UDisks2 enumeration. Optional `python3-pyqt6` allows a real
offscreen Qt style instantiation; without it that probe is **SKIPPED**. It does
not attach to an active Dolphin window or pretend to inspect its live widgets.

Actual Dolphin was separately launched and its widget tree/screenshots inspected
on an isolated Wayland compositor in Debian 13 WSL. The real installer, component
verifier and restore all passed. Tests cover 1920×1080, a 1100×680 window on
1366×768, and a 3840×2160 output at scale 2. Places/Information are right-aligned
and vertically stacked; Folders/Terminal are hidden. Actual JPEG thumbnails and
selected-item metadata work, and UDisks2 exposes device rows in that environment.

This is not the user's physical Hyprland session. Exact visual comparison with
the missing reference, Hyprland's blur/opacity, the real monitor scaling and
mounting/ejecting physical removable drives still require validation on the PC.
No device was mounted, unmounted or formatted during validation.

Primary references: [Debian Dolphin package](https://packages.debian.org/trixie/dolphin),
[Dolphin general settings](https://github.com/KDE/dolphin/blob/v25.04.3/src/settings/dolphin_generalsettings.kcfg),
[Dolphin dock setup](https://github.com/KDE/dolphin/blob/v25.04.3/src/dolphinmainwindow.cpp),
[view-property migration](https://github.com/KDE/dolphin/blob/v25.04.3/src/views/viewproperties.cpp),
[Baloo metadata defaults](https://github.com/KDE/baloo-widgets/blob/v25.04.0/src/metadatafilter.cpp),
[KF6 window-state storage](https://github.com/KDE/kxmlgui/blob/v6.13.0/src/kmainwindow.cpp),
[Debian thumbnail plugin files](https://packages.debian.org/trixie/amd64/kio-extras/filelist).
