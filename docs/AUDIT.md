# Technical audit

> Historical audit of the initial cleanup, not the current v1 guide. Version
> targets, filenames and counts below describe that stage of the project.
> Use the [documentation index](README.md) and [current release review](release-readiness.md)
> for the present configuration. This record is retained for provenance.

## Scope and method

Baseline: commit `f96dfb4`, the original repository with no local changes.
**593 files** were inventoried, with 588 text files decoded in full; binary
assets were identified and hashed. The figure given in the first progress
update was an estimate, replaced here by the exact inventory count.

The original inventory records each file's path, size and SHA256:
[inventory-original.tsv](inventory-original.tsv). Script roles, dependencies
and links to startup/keybinding entry points were examined before
reorganization. The review distinguished installed features, generic KoolDots
examples and generated VM state.

## Issues addressed

| Original finding | Resolution |
| --- | --- |
| Duplicate global `LIBGL_ALWAYS_SOFTWARE` forcing | Removed from the native tree; separate explicit profile |
| Hyprlock launched with three Mesa overrides | Normal native launcher; optional environment supplied by the profile |
| Several conflicting generic monitor rules, followed by `Virtual-1` | One wildcard rule, preferred mode, automatic scale/position |
| Workspace 1 tied to the VM display | No workspace tied to a connector |
| Two wallpaper systems and a 3-second delay | One script, flock lock, bounded wait for IPC/outputs |
| awww daemon killed and restarted | Reuse the daemon; start it if missing, without killing it |
| Duplicate wallpaper and tracked per-monitor caches | One source image; Hyprlock uses the installed image directly |
| Waybar config/style files containing only a `/home/luc/...` path | Actual JSON/CSS files with imports resolved and rendered during installation |
| Overlapping KoolDots and ALT bindings, with two ALT+Tab actions | One native binding table, checked for duplicates |
| Duplicate SUPER+Tab group/workspace actions | Ambiguity removed; PageUp/PageDown for workspaces |
| Qt Widgets tested as a QML module, unjustified Fusion fallback | Kvantum for Widgets, Basic for Qt Quick, Qt6 plugin checked |
| NVIDIA variables and software cursor forced for all GPUs | No forced driver in native; software cursor limited to the VM profile |
| Quickshell/overview/Kitty autostarts without associated files | Removed from active startup; optional examples preserved separately |
| Tokyo Night palette in Alacritty | Initially aligned with Frosted Glass; later replaced by the Kitty migration, preserving the palette, 0.92 background opacity and 10 px padding |
| Duplicate Waybar CSS, power button defined twice, once in pink | A single Frosted-Glass stylesheet, shared colors for the power button |
| Package list taken from the VM | Active dependencies, backports, optional packages and guest integration separated |

## Preserved features

The original wallpaper and Kvantum files are verified by SHA256. The Dolphin
toolbar and interface defaults are restored byte for byte from pre-9259fa5 Git
history and checked against saved hashes. A separate Dolphin-only Kvantum paint
variant and per-application KDE color scheme leave other Qt apps unchanged.
See the current [Dolphin guide](dolphin-kvantum.md).
Decoration values are unchanged: rounding 13, active opacity 0.78 /
inactive 0.72, blur size 4 / 3 passes, gaps 4/10, 2 px borders and the same
colors. Rofi retains its KoolDots/adi1090x layout and translucent palette.
Waybar retains its colors/background and top position; MPRIS, the tray and
idle inhibitor are also preserved.

The active applications are Kitty/Dolphin; audio, media, brightness,
screenshots, notifications, clipboard, gestures and window/workspace
management remain accessible. Alt+F10 remains a graphical switcher.
The primary Alt+Tab navigation uses the official Lua dispatcher, without
a workaround for Wayland crashes in the VM.

Alternative themes, weather/music, quick settings, version repairs, SSH
scripts, SDDM/dock/Quickshell tools and settings for other distributions are
identified as an optional library in `extras/kooldots`. They are not deployed.
Their syntax is checked; their external references do not constitute a
guarantee that they work in Hyprixe.

## Reasons for removals

- Old `backup-before-tokyonight` backup, first-boot markers and wallpaper
  cache files: generated state, unnecessary for installation.
- Three wallpaper copies and a generated modified version: the single
  original remains in `wallpapers/min_forest.jpg`.
- Old `SetFrostedWallpaper.sh` script: replaced by `Wallpaper.sh`, with
  output detection and no native graphics overrides.
- Old Kitty theme collection and dedicated Thunar launcher: unused files removed;
  generic upstream selection scripts remain as optional references.
- Precompiled `dots-tui-ubuntu-2404` binary (~17.7 MB): a tool for another
  distribution, not launched by the target configuration, without bundled source.
- Old Senshi-Tokyo-Night names: replaced by Frosted-Glass.

Thunar/Tokyo references remain only in generic examples and historical audit
documents. Kitty was subsequently restored as the active terminal with one
minimal Frosted Glass configuration, without the old theme collection. See
[terminal guide](kitty-zsh.md). VM monitor examples are kept only under
`profiles/vmware/monitor-examples` and are never applied automatically.

## Security and limitations

No GitHub/AWS token or private-key patterns were found in the current files
or in the single historical commit. File names were also checked for `.env`,
credentials, cookies, shell history, logs and caches. VM caches were removed,
ignore rules expanded, and temporary/test copies excluded from tracking.
Tests do not trigger locking, suspend or shutdown.

The installer rejects root for deployment, limits targets to HOME, rejects
symlinked parent directories, backs up each file, protects backups and
checks their hashes. Upstream network/build operations use pinned revisions
and run without elevated privileges; APT uses signed repositories.
Archived optional system tools are never run.

The exact Senshi/wallpaper provenance still needs to be completed: see CREDITS.md.
WSL tests do not establish rendering quality, physical PC device behavior,
PAM unlocking or resume from suspend. These checks are explicitly SKIPPED
and require the INSTALL.md procedure on the target machine.
