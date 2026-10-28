# Installing Hyprixe Debian

## Prerequisites

- Debian GNU/Linux **13 (trixie)**, a regular user account, access to `sudo`,
  a network connection and several GB of free space for APT and the first builds.
- DRM/Mesa or NVIDIA drivers suitable for the hardware, and a working
  logind/DBus session. This repository does not install proprietary drivers
  automatically.
- An existing Debian **SDDM with its Qt 6 greeter** (`sddm-greeter-qt6`).
  Select **Hyprland (uwsm-managed)** after installation. The installer checks
  SDDM first; it does not replace a different display manager or configure autologin.
  If SDDM is not installed, an administrator must install/select it beforehand
  (`sudo apt install sddm`). Replacing an existing display manager remains an
  explicit administrator choice.
- Hyprland **0.56.2** is the reference version for this Lua configuration and
  the working version reported by the user. Its APIs and options were checked
  against the upstream v0.56.2 tag. **0.55.2 remains the minimum accepted version**
  for the installer: 0.55.2+ does not require downgrading to 0.55.2.
  The trixie-backports metadata consulted lists `0.55.2+ds-1~bpo13+1`;
  keep your working 0.56.2 installation. The script does not pin an exact
  APT version. Versions below the minimum are rejected before copying files.

If `sudo`/`git` are missing, install them from an administrator account, then
return to the account that will run the graphical session:

```bash
su -
apt update
apt install sudo git
usermod -aG sudo YOUR_ACCOUNT
exit
# Log out and back in to activate sudo group membership.
```

## Installation

Close Dolphin and configuration editors to prevent them from
rewriting their preferences while files are being copied.

```bash
git clone https://github.com/pixe71/hyprixe-debian.git
cd hyprixe-debian
./install.sh
```

Equivalent commands and options:

```bash
./install.sh native
./install.sh vmware
./install.sh --dry-run
./install.sh native --no-packages
```

Do not run `sudo ./install.sh`. Deployment runs under your account;
only APT and SDDM system installation/restoration use `sudo`.
If the executable bits were lost when copying
the repository, run `chmod +x install.sh uninstall.sh verify.sh scripts/build-runtime.sh`.

The `--dry-run` mode shows which paths would change, without running APT or
copying files. It does not guarantee that dependencies are already installed.
It also previews SDDM paths without `sudo` or system changes.
`--no-packages` checks commands, the Hyprland version, Rofi's Wayland/button capabilities
and the Qt6 Kvantum plugin; it fails before touching configuration files if
any requirement is missing.
It also requires the SDDM Qt 6 modules in `packages-sddm.txt` and the existing
Debian UWSM session entry. Both real installation modes include the login theme.

Use the normal `./install.sh native` command to repair missing awww or an
incompatible Rofi/Waybar. `--no-packages` also skips runtime builds; it cannot
prepare those missing capabilities. The installer reuses suitable binaries
already present in `~/.local/bin` and builds only what is missing or incompatible.

## Dependencies and system changes

`packages.txt` lists the Debian stable applications actually used.
`packages-backports.txt` lists Hyprland, UWSM, Hyprlock, Hypridle, XWayland and the
Hyprland portal. `packages-optional.txt` is optional. The VMware profile
also installs the packages in `profiles/vmware/packages.txt`.
`packages-sddm.txt` contains the Qt 6 Quick, Controls, Templates, Layouts,
Effects, Window, WorkerScript and SVG runtime packages for the login theme.
These use normal Debian APT candidates, without a global backports switch.

If no trixie-backports repository is configured, the installer creates only
`/etc/apt/sources.list.d/hyprixe-backports.sources`, pointing to the official
Debian repository signed with the Debian key. An existing file at that path
is not overwritten. Hyprland packages are explicitly requested from
trixie-backports.

Debian stable provides Rofi 1.7.5 for X11 in the indexes used during the audit;
awww is not packaged there. When needed, `scripts/build-runtime.sh` builds:

| Program | Source and pinned revision |
| --- | --- |
| Rofi 2.0.0, Wayland | `davatorium/rofi`, `0b6aa8ba8b4879f00c3cc96f2e47a13c079fe814` |
| awww 0.12.1 | `codeberg.org/LGFae/awww`, `f66e12a76dbc4c669b2f1375f78bce49f5b19d66` |
| Waybar 0.12, if Lua IPC support is missing | `Alexays/Waybar`, `8490a1d9b9a5c8770dd63e9faca0a5e01acedcae`, with a limited local adaptation in `scripts/waybar-lua-ipc.hpp` |

The script verifies commits, initializes submodules at their recorded revisions
and uses `cargo build --release --locked`. It installs the C/Meson tools and
Rust/Cargo backports needed for compilation. Sources are built without elevated
privileges in a temporary directory that is removed afterwards.
The resulting executables are deployed to `~/.local/bin` using the same backup
system as the configuration files. Existing versions with the required
capabilities are reused.
The application launcher's sidebar also requires the scoped button support in
`scripts/rofi_launcher.py`. The installer applies it to the pinned Rofi source
before building. A previously installed Wayland build without this capability is
rebuilt automatically; use `./install.sh native` without `--no-packages` for this
update. No new launcher framework or runtime package is added. Other Rofi menus
keep upstream behaviour. Details: [Rofi application launcher](docs/ROFI.md).
Waybar support is detected by checking for its compiled Lua IPC commands,
without sending actions to the compositor. Stable Waybar 0.12 lacks this
support: the prepared build converts only workspace changes to
`hl.dsp.focus` / `hl.dsp.workspace.toggle_special`. JSON read requests,
modules and CSS are unchanged. The patch is identified by
`hyprixe-lua-ipc1` in `waybar --version`. Required C++/GTK headers are installed
through APT if this build is needed.

Build dependencies are selected by `scripts/apt-build-deps.py`. It inspects
installed Debian package source families and direct/indirect header dependencies.
If a runtime family is already installed from Debian 13 backports, its required
headers are explicitly requested as `PACKAGE/trixie-backports`. In particular,
backported `libxkbcommon0` or `libxkbregistry0` selects both `libxkbcommon-dev`
and `libxkbregistry-dev` from that suite. Other build dependencies keep their
normal APT candidates; there is no global backports target or persistent pin
for the build dependency transaction. The same selection is used for Rofi and awww.

Build dependency installation prohibits package removals and automatic downgrades.
If matching headers are unavailable, preparation stops with an error instead of
falling back to stable headers. The installer refreshes APT indexes before this
selection. To inspect the real resolver plan without installing anything:

```bash
python3 scripts/apt-build-deps.py --simulate waybar
```

Hyprland's PATH includes this directory. For diagnostic commands from an
existing console, run `export PATH="$HOME/.local/bin:$PATH"`.

APT/Cargo/Git downloads require network access. If a build fails, user
configuration files are not deployed; APT packages already installed remain
in place. No `curl | sh` command is used.

## Modified files and backups

The installer copies configuration from `.config/`, theme assets under
`.local/share/`, and the wallpaper to
`~/.local/share/hyprixe/wallpapers/min_forest.jpg`. It never copies `extras/`.
Existing Dolphin interface preferences and its toolbar are preserved; fresh
installations receive the original pre-9259fa5 interface files. Only the
Dolphin-specific `UiSettings/ColorScheme` key is merged for color integration.
No dock state, global view properties or icon-size preset is deployed.
It selects `profile.lua` and `profile.env` from the requested profile.

The relevant values in `mimeapps.list`, `kdeglobals` and `qt6ct.conf` are
merged: other MIME associations, groups and preferences are preserved.
The session-specific `hyprland-mimeapps.list` also receives the directory
association so an older session-specific choice cannot take priority.
Dolphin becomes the application for `inode/directory`. Kitty is the
terminal for Hyprland, Rofi and KDE. Qt Widgets uses Kvantum; Qt Quick uses Basic.

Kitty is installed from Debian stable and configured through
`$XDG_CONFIG_HOME/kitty/kitty.conf` (normally `~/.config/kitty/kitty.conf`).
Existing Kitty settings are backed up before replacement. Alacritty is no
longer required; its installed package and personal settings are left intact.
After migrating, log out and select **Hyprland (uwsm-managed)** again so
`TERMINAL=kitty` is imported into the fresh session. Details and restore steps:
[Kitty Frosted Glass](docs/TERMINAL.md).

A `systemd/user/waybar.service.d/hyprixe.conf` drop-in supplies the selected
Waybar executable and configuration paths to Debian's Waybar service. Its
`PartOf=`, `After=` and `Requisite=graphical-session.target` dependencies are
preserved. Hyprixe requests the service through its own session target, even
if Waybar was not previously enabled. No direct Waybar fallback bypasses those
dependencies. The drop-in is also backed up and restored.

The Waybar service uses `hypr/waybar/configs/Frosted-Glass` directly with `-c`
and `hypr/waybar/style.css` with `-s`. The old `hypr/waybar/config` JSON include
wrapper is no longer required or generated. These paths follow XDG_CONFIG_HOME,
including paths containing spaces. The stylesheet keeps its relative import
of `style/Frosted-Glass.css`. Installation refuses to deploy if any of these
three active Waybar files is missing. An old wrapper already in your personal
configuration may remain; the managed launchers do not read it.

After updating from the wrapper-based layout, run `./install.sh native --no-packages`
to deploy the updated launcher and systemd drop-in, then run
`./verify.sh --dependencies`. Use the same profile you selected previously.
The existing backup and restore behavior still applies.

The installer also deploys `hyprixe-session.target` and units for the persistent
awww daemon, wallpaper application, clipboard watcher and authentication agent.
The target reuses Debian's `waybar.service`, `hypridle.service` and `swaync.service`.
A Hypridle drop-in provides its explicit XDG configuration path. All these files
use the existing dated backup and restoration mechanism; no persistent service
enablement is needed. The startup hook calls `uwsm finalize` after Hyprland has
set its environment, then queues only `hyprixe-session.target`. UWSM activates
and cleans up `graphical-session.target`; Hyprixe never starts it manually.
The wallpaper daemon stays in its own service when the image-application
oneshot finishes, and is stopped when the graphical session ends.
Static services read UWSM's per-session `env_session.conf`, so transient login
metadata is not placed in the global manager environment. Hypridle explicitly
locks `$XDG_SESSION_ID`, which is necessary when its process runs as a user
service outside the login session's process scope.

An old `hypr/hyprland.conf` is backed up and removed so it cannot take
precedence over the Lua entry point. Additional personal files are not deleted.
Existing managed files are backed up **before any writes**.

```text
~/.local/state/hyprixe/backups/DATE_UTC-PROFILE/
├── manifest.json     paths, before/after state, hashes and permissions
├── files/            original files, including symbolic links
└── complete          completed transaction
```

Backups are private (directory mode `0700`). A copy error rolls back writes
already performed. A second identical installation copies nothing and creates
no additional backup. Reinstalling after personal edits backs up the edited
version.

XDG_CONFIG_HOME, XDG_DATA_HOME and XDG_STATE_HOME are accepted if they point
to absolute, real subdirectories of HOME. Hyprlock, Rofi, Hypridle and Waybar
paths are rendered accordingly. Symlinked parent directories are rejected to
avoid writing through another dotfile manager: back up and detach those links
first, then run the installer again.

## Restore / uninstall

```bash
./uninstall.sh --list
./uninstall.sh --dry-run
./uninstall.sh
./uninstall.sh --backup ID_FROM_LIST
```

By default, the latest transaction that has not been restored is undone.
Previous files regain their contents and permissions; files created by that
transaction are removed. Only directories created by the transaction that
are now empty are removed. Other personal files remain in place.

If an installed file has since been edited, restoration refuses the entire
operation and lists the affected paths. Copy your edits elsewhere, return those
files to their installed state, then try again. No destructive `--force` option
is provided. Backup hashes are verified before restoration.
For Dolphin's expected runtime writes, `--save-dolphin-changes` first preserves
the changed managed Dolphin files/view xattr in the chosen backup, then restores
their originals. Unrelated-file conflicts still block the whole operation. See
[the Dolphin restore procedure](docs/DOLPHIN.md#restore).
To return to the state before several installations, undo transactions from
newest to oldest; do not delete intermediate backups. An interrupted restore
can be run again.

APT packages and the backports repository are not removed automatically.
They may be used by other applications; manage their removal separately with
APT. Log out and back in after restoring or changing profiles.

## SDDM Frosted Glass login screen

`./install.sh native` and `./install.sh vmware` install the same original
`hyprixe-frosted` theme. SDDM must already be installed; Qt 6 runtime modules are
installed from `packages-sddm.txt` unless `--no-packages` was requested. The
installer preserves SDDM's greeter display-server backend, PAM, autologin,
session commands, session desktop files and UWSM. It disables the greeter's
virtual keyboard and orders the desktop services after the wallpaper request.
The last selected user/session comes from SDDM's own models. Choose
**Hyprland (uwsm-managed)**; selecting plain Hyprland still starts the plain
session and is diagnosed by `./verify.sh --session`.

System paths managed through `sudo`:

| Path | Contents / behavior |
| --- | --- |
| `/usr/share/sddm/themes/hyprixe-frosted/Main.qml` | Responsive login screen, user/session models and SDDM login/power API |
| `/usr/share/sddm/themes/hyprixe-frosted/components/` | Glass panel, button and session/account ComboBox components |
| `/usr/share/sddm/themes/hyprixe-frosted/assets/user.svg` | Original fallback avatar; SDDM's supplied avatar is used when available |
| `/usr/share/sddm/themes/hyprixe-frosted/metadata.desktop` | Theme metadata selecting Qt 6 |
| `/usr/share/sddm/themes/hyprixe-frosted/theme.conf` | Wallpaper name and font |
| `/usr/share/sddm/themes/hyprixe-frosted/min_forest.jpg` | Exact copy of `wallpapers/min_forest.jpg`; no second source copy in Git and no dependency on a user's home permissions |
| `/etc/sddm.conf.d/zz-hyprixe-theme.conf` | `[Theme]` with `Current=hyprixe-frosted` and `ThemeDir=/usr/share/sddm/themes`; `[General]` with empty `InputMethod=` |
| `/var/lib/hyprixe/sddm/backups/UTC-sddm-ID/` | Private root-owned manifest and originals, including modes/owners and hashes |

SDDM reads `/etc/sddm.conf` **after** the configuration snippets. If it, or an
alphabetically later local snippet, sets `[Theme] Current` / `ThemeDir` or
`[General] InputMethod`, the
installer backs up that file and replaces only those overriding lines with
comments. All other settings and comments remain. The dedicated snippet becomes
the effective selection, verified after installation. Earlier and vendor snippets
are left untouched. Symlinked system targets are refused with a clear error.

Every overwritten system file is backed up before any system writes. Installation
is idempotent; an identical rerun creates no extra backup. A system deployment
error rolls back its successful writes and the new user deployment. The root
backup ID is recorded in the corresponding user transaction so the ordinary
`./uninstall.sh` can restore both. When only SDDM changed, a user restore entry
is still created. Other SDDM themes and additional personal theme files remain.
APT packages are retained on restore.

Reboot after installation so SDDM reads the new selection. No automatic restart
or service enablement is performed. For a safe windowed preview from an existing
graphical session, run as your normal user:

```bash
sddm-greeter-qt6 --test-mode --theme /usr/share/sddm/themes/hyprixe-frosted
./verify.sh --sddm
./verify.sh --dependencies --session   # inside Hyprland (uwsm-managed)
```

`--sddm` checks installed file bytes, wallpaper, readability, effective theme
selection, Qt 6 runtime modules, and the packaged UWSM desktop entry and session
search path. `--dependencies` includes these checks too. Plain `./verify.sh`
checks the repository theme without requiring a system deployment. Optional
`qt6-declarative-dev-tools` enables `qmllint`; `python3-pyqt6.qtquick` enables the
isolated Qt interaction test. Missing optional validators report **SKIPPED**.
The interaction test uses a mocked SDDM proxy; it never authenticates or reboots.

The desktop greeter uses `[General] InputMethod=` to disable Qt Virtual Keyboard
without changing password focus, the physical keyboard, layouts or PAM. No
`InputPanel`, Qt Virtual Keyboard import or `Qt.inputMethod.show()` is present
in the theme. Installation and verification reject a theme that forces such a
panel. Higher-priority input-method settings are backed up with the theme;
ordinary restore, or `./uninstall.sh --sddm-only`, restores their previous values.
No shared Qt keyboard packages are removed.

The wide layout places the clock on the left and the glass form on the right;
smaller widths stack them. Short screens can scroll the form to reach the
session selector. Qt's logical pixels and SDDM's existing HiDPI configuration are
used without changing global DPI settings. The glass blur samples the wallpaper
through Qt Quick Effects, independently of Hyprland's compositor blur.

### Recover only the previous SDDM theme

If the greeter has a problem, switch to a TTY with **Ctrl+Alt+F3**, log in to your
normal account, and run:

```bash
cd ~/hyprixe-debian
./uninstall.sh --sddm-only --list
./uninstall.sh --sddm-only --dry-run
./uninstall.sh --sddm-only
# Or select a specific system backup from the list:
./uninstall.sh --sddm-only --backup SYSTEM_BACKUP_ID
```

These commands use `sudo` to access the private system backup and restore just
the files/theme selection managed by that transaction. They do not depend on
unchanged personal Hyprland files and do not touch your desktop configuration.
The default selects the newest unrestored SDDM transaction belonging to the
installing user. Undo multiple transactions from newest to oldest if needed.
Changed installed system files block restoration before any files are changed;
save those edits elsewhere and restore their installed contents first.
After recovery, reboot when your work is saved so SDDM rereads its configuration.
Do not manually delete the dedicated snippet: a higher-priority original theme
setting may also need restoration from the backup.

References: [SDDM theme interface](https://github.com/sddm/sddm/blob/develop/docs/THEMING.md),
[Debian SDDM configuration precedence](https://manpages.debian.org/trixie/sddm/sddm.conf.5.en.html),
[Qt 6.8 MultiEffect](https://doc.qt.io/qt-6.8/qml-qtquick-effects-multieffect.html).

## First launch

Log out completely and select **Hyprland (uwsm-managed)** in SDDM, then log in.
After first installing the login theme, reboot to ensure SDDM rereads its system
configuration. Installation never restarts the display manager automatically.
Debian provides `/usr/share/wayland-sessions/hyprland-uwsm.desktop`, whose command
is `uwsm start -e -D Hyprland hyprland.desktop`. The plain **Hyprland** entry
uses `/usr/bin/start-hyprland`; it can run the compositor and import its
environment without providing the UWSM lifecycle expected by these services.
Installing UWSM or running `hyprctl reload` does not convert that existing
session: log out and choose the managed entry.

For the one-time migration from an already running plain session, save your
work and exit that session with `hyprctl dispatch 'hl.dsp.exit()'` if needed.
Once using UWSM, use the power menu or `uwsm stop` for logout instead.

From a local console without a display manager, use the same UWSM command in
a normal logind login session. Do not start a second compositor inside an
existing graphical session:

```bash
uwsm start -e -D Hyprland hyprland.desktop
```

```bash
Hyprland --version
hyprctl version
hyprctl configerrors
hyprctl monitors -j
hyprctl binds -j
./verify.sh --dependencies --session
uwsm check is-active -v compositor-only
systemctl --user is-active graphical-session.target
systemctl --user status hyprixe-session.target waybar.service hypridle.service swaync.service --no-pager
```

`graphical-session.target` must be active. A missing `hyprland-session.target`
is not an error in this architecture: UWSM supplies `wayland-wm@...` and
`wayland-session@...` units. Do not create or start a graphical target manually,
and do not remove Waybar's `Requisite=` to work around a plain-session login.

`./verify.sh --session` is read-only. It diagnoses a missing UWSM compositor,
an inactive graphical target, stale/missing manager environment, and inactive
or failed session services, with the appropriate journal commands. Run it
from a terminal inside the managed Hyprland session, not from an unrelated TTY.

`configerrors` should be empty. Monitors should match the hardware.
The default rule uses each output's preferred mode and scale.
To customize an output, edit `UserConfigs/monitors.lua` after checking
`hyprctl monitors`, then run `hyprctl reload`.

Workspaces 1–4 are real persistent Hyprland workspaces, defined by concrete
`hl.workspace_rule` entries in `lua/workspaces.lua`, without a monitor binding.
Waybar uses `persistent-workspaces: {"*": [1, 2, 3, 4]}` and numeric sorting
to keep those four buttons visible on the left. Workspaces 5–10 remain dynamic.
To inspect compositor state, use `hyprctl workspaces -j` and
`hyprctl workspacerules -j`, including after emptying a workspace and leaving it.

Lua modules are loaded explicitly. To reload after an edit:

```bash
hyprctl reload
hyprctl configerrors
```

Environment/profile changes and the Hyprlang → Lua transition require
a new session, even if reloading reports no errors.

## Checking components

### Waybar module layout

The organization is inspired by Hyprladus' module grouping; its theme, colors,
Powerline separators, Arch scripts and 10-workspace preset are not imported.
Hyprixe keeps its existing Frosted Glass CSS. The native click drawer precedes
workspaces 1–4 and the unchanged icon taskbar. The Debian logo is centered between
temperature/storage, RAM, CPU and time, date, idle inhibitor. Network, Bluetooth,
audio, optional battery percentage and the existing power menu sit on the right.

Update only Waybar on an existing installation, without closing Dolphin:

```bash
cd ~/hyprixe-debian
git pull
./install.sh native --waybar-only --no-packages
systemctl --user restart waybar.service
systemctl --user status waybar.service --no-pager
./verify.sh --waybar --session
```

Run this inside the existing **Hyprland (uwsm-managed)** session. Scoped mode uses
the installed compatible Waybar and fontconfig; it performs no APT/system writes,
changes no other component, and creates a dated `*-native-waybar` backup. It
updates Waybar JSON/CSS, the adaptive sensor helper and the tiny isolated Debian
glyph font. A normal full installation also includes these assets.

Missing native drawer/taskbar/Lua support is a clear preflight failure; use the
normal full installer to prepare the pinned Waybar build. `--dry-run` previews
changes. Existing strict restore (`./uninstall.sh --backup ID`) restores this
transaction without touching unrelated files. See [docs/WAYBAR.md](docs/WAYBAR.md)
for detection rules, font provenance, calendar locale and hardware limits.

### Waybar application icons

`wlr/taskbar` uses Wayland's foreign-toplevel protocol, supported by Hyprland
0.56.2 and the prepared Waybar 0.12 build. Focus requests use that protocol
directly; they do not depend on legacy Hyprland dispatch strings or a polling
script. Each window gets its own button, so two Dolphin or Kitty windows
remain independently accessible. All outputs/workspaces are included without
a hardcoded monitor, and activating a window can switch to its workspace.

The icons are 16 px, use Breeze with GTK's existing fallback, and show only the
window title on hover. The active window has a blue fill/cyan outline. Button
positions remain stable on focus changes; the module collapses when empty.

For an existing working Hyprixe installation, apply the update without rebooting:

```bash
cd ~/hyprixe-debian
git pull
./install.sh native --waybar-only --no-packages
systemctl --user restart waybar.service
./verify.sh --waybar --session
```

Run those commands inside **Hyprland (uwsm-managed)**. If dependency preflight
reports a Waybar missing `wlr/taskbar`, use `./install.sh native` to prepare the
compatible build, then restart Waybar. The current prepared build already
contains the module, so normally no rebuild is needed. Existing backups/restore
cover the JSON and CSS changes. Check two windows of the same app, switch focus
using their icons, and confirm the four workspace buttons still work.

### Screenshots

| Shortcut | Action |
| --- | --- |
| SUPER + SHIFT + S | `slurp` selection, `grim` capture, then PNG to `wl-copy`; no persistent screenshot file |
| Print | Save the entire desktop (all outputs) to `~/Pictures/Screenshots/` |
| SHIFT + Print | Select an area and save to `~/Pictures/Screenshots/` |
| SUPER + Print / SUPER + SHIFT + Print | Existing full/area shortcuts: save under the XDG Pictures directory and copy to the clipboard |

The new save-only shortcuts use the exact `Pictures/Screenshots` path below HOME,
including when Debian's localized XDG Pictures directory is `Images`. They create
that directory on the first successful capture and preserve the current
clipboard. The legacy shortcuts continue to respect `xdg-user-dir PICTURES`.
Delayed, active-window and optional Swappy modes remain available.

Names have a readable local timestamp and an atomically reserved unique suffix,
for example `Screenshot-2026-10-26_21-30-15-a1B2c3.png`. Existing files cannot be
overwritten by simultaneous captures. Escape/cancel creates no file and leaves
the clipboard unchanged. Capture failure is reported before any clipboard write;
temporary images are cleaned up automatically. Notifications are non-critical.

`grim`, `slurp` and `wl-clipboard` are already in the repository's dependencies.
No additional package is needed on a working Hyprixe installation. To update:

```bash
cd ~/hyprixe-debian
git pull
./install.sh native --no-packages
hyprctl reload
hyprctl configerrors
./verify.sh
```

Run this from Hyprland. No logout or reboot is required. Test the three shortcuts,
including Escape during selection and pasting the copied image into an application
that accepts images. The verifier checks the Lua bindings for duplicates and
retains the old combinations. Script tests cover cancellation, concurrent names,
clipboard preservation, failed capture and the previous save/copy modes.

### Other components

```bash
# Waybar: request Debian's service inside an active UWSM session.
~/.config/hypr/scripts/WaybarStartup.sh
# Reload the CSS/configuration of an existing instance:
systemctl --user reload waybar.service

# Wallpaper: reuse the daemon and detect all outputs.
~/.config/hypr/scripts/Wallpaper.sh
awww query

# Interactive locking (test with the account password).
~/.config/hypr/scripts/LockScreen.sh

# Applications
kitty
dolphin
~/.config/hypr/scripts/RofiLauncher.sh
xdg-mime query default inode/directory
```

Kitty, Dolphin, the Rofi launcher and Hyprlock use `uwsm app --`, as
recommended for applications in a systemd-managed compositor session.
Rofi's `run-command` also prefixes selected applications with `uwsm app --`.
Existing keyboard combinations and other applications are unchanged. Short control
commands such as focus, volume and brightness remain direct commands.
The power menu's logout action calls `uwsm stop` for ordered session teardown.

### Rofi application launcher

`SUPER + Space` retains native `drun` search, application icons, typing, arrows,
Enter and Escape. Its dedicated `config-launcher.rasi` imports the existing theme
and adds a centered 60% × 58% layout. The left panel occupies approximately 44%
of the content and displays the already installed `min_forest.jpg`; the right
panel keeps the search field and application list. No wallpaper copy is added.

The four vertical buttons are Applications (return to native `drun` in the same
instance), Files (Dolphin), Windows (the existing `WindowSwitcher.sh`) and Terminal
(Kitty). The launcher explicitly uses `uwsm app -t scope --` to wait for its return
code even if `UWSM_APP_UNIT_TYPE` is overridden elsewhere. After Rofi closes,
Files and Terminal delegate to the existing UWSM helpers; Windows reuses the
existing switcher. No global environment variable or Hyprland rule is changed.

Apply and check the update:

```bash
git pull
./install.sh native
./verify.sh --dependencies --session
```

No logout or keybinding reload is required: the existing binding calls the updated
script. Test `SUPER + Space`, immediate typing, Enter/Escape and all four buttons.
Visual blur and the final appearance must be checked in the physical Hyprland
session. Use the existing `./uninstall.sh --list` / dated restore mechanism to
restore the previous configuration and any Rofi binary replaced by this update.

### Wlogout session menu

The full installer also installs Debian's `wlogout` and SVG loader
`librsvg2-common`, deploys `wlogout/layout`, `style.css`, four local icons and
the `~/.local/bin/hyprixe-session` helper, and backs up their previous versions.
`SUPER + Backspace` opens/closes the four-button horizontal Frosted Glass menu:
**Lock | Logout | Shutdown | Reboot**. The existing Waybar power menu is retained.

After updating, run `hyprctl reload`, then `hyprctl configerrors` and
`./verify.sh --dependencies --session` inside your managed Hyprland session.
No SDDM restart is needed for Wlogout. Test arrows, Enter and Escape; Logout,
Shutdown and Reboot ask for confirmation with Cancel selected by default.
Logout uses `uwsm stop`. To revert, restore the matching dated transaction
with `uninstall.sh` and reload Hyprland. Details: [Wlogout](docs/WLOGOUT.md).

If XDG_CONFIG_HOME is customized, replace `~/.config` in these manual commands.
Session scripts already use the XDG variables.

Hyprlock reads the same image as awww, directly from the data directory:
it does not depend on a cache generated during startup. Test locking and
unlocking before using suspend. Hypridle locks after 10 minutes and turns
outputs off after 12 minutes. There is no automatic suspend; Waybar's idle
inhibitor can pause idle handling.

### Dolphin appearance and original interface

Dolphin 25.04 / Qt 6 retains its previous interface. Its original toolbar and
`dolphinrc` are restored in the repository; the 96 px/right-column preset from
`9259fa5` is removed. The **Frosted-Glass-Dolphin** Kvantum variant paints neutral off-white
translucent surfaces with restrained cyan accents. A matching KDE color scheme selected only in Dolphin
prevents KDE from restoring a light palette over it. Other Qt applications keep
the global Frosted-Glass theme; Breeze Dark icons are unchanged.

For a PC that received the rejected layout, close Dolphin normally, then run:

```bash
cd ~/hyprixe-debian
git pull
./install.sh native --dolphin-only --restore-dolphin-interface
./verify.sh --dolphin
uwsm app -- dolphin
./verify.sh --dolphin --session
```

The one-off restore selects the oldest intact deployment backup whose toolbar
matches `9259fa5` and whose original toolbar differs. It restores only the saved
Dolphin interface/state/view files and original group visibility. Other desktop
files and newly added bookmarks are retained. The operation itself is backed up;
a marker prevents repeating it over later user adjustments. If no matching
backup exists, it stops without installing a substitute interface. Inspect
`./uninstall.sh --list`; an explicit selection can be supplied as
`--interface-backup=ID` alongside the restoration flags.

For subsequent visual updates, use `./install.sh native --dolphin-only` without
the restoration flag. This mode deploys the Kvantum SVG/config, its Dolphin
association, the KDE color file and only `UiSettings/ColorScheme` in `dolphinrc`.
It does not change docks, toolbar, icon size, view mode, shortcuts or navigation.
No Hyprland, UWSM, SDDM, Waybar or profile file is deployed by this mode.

Missing Qt6/Kvantum/thumbnail/device packages are installed from
`packages-dolphin.txt`. `--no-packages` requires them already installed;
`--dry-run` previews without creating backups or writing configuration.
`QT_STYLE_OVERRIDE=kvantum` is already exported by Hyprland and UWSM finalization;
no Fusion fallback or compositor opacity workaround is added.

See [docs/DOLPHIN.md](docs/DOLPHIN.md) for colors, file paths, scoped restoration,
actual validation and physical blur limitations.

## Troubleshooting and limitations

### Login transition / white flash diagnosis

The managed startup sequence is:

```text
Hyprland starts with the Frosted Glass base color (#122434), without its splash
  -> SessionStartup reloads the user unit definitions
  -> uwsm finalize activates the UWSM graphical lifecycle
  -> graphical-session.target
  -> hyprixe-awww.service (persistent daemon)
  -> hyprixe-wallpaper.service (bounded IPC/output readiness, immediate image)
  -> Waybar / SwayNC and the other Hyprixe session services
```

The Waybar and SwayNC drop-ins pull in the wallpaper service with `Wants=` and
wait for its oneshot with `After=`, including when Debian's Waybar was already
enabled independently. The wallpaper unit is also ordered before Hypridle,
the authentication agent and clipboard watcher in the Hyprixe startup transaction.
UWSM still owns `graphical-session.target`; no manual graphical-target start or
Waybar dependency removal is used. A wallpaper failure is logged and does not
prevent Waybar from running after the failed job completes.

`awww img --transition-type none` replaces the old one-second startup fade.
The only polling interval is the existing 100 ms readiness retry, bounded at
5 seconds; it stops immediately when IPC and all current outputs are ready.
An initially empty Hyprland monitor query is retried, not treated as a completed
startup. There is no unconditional sleep or greeter-closing delay. An early
monitor-added callback before UWSM finalization leaves initial application to the
session unit instead of starting a daemon outside the session ordering.

These changes address a known parallel/fading wallpaper startup, but do **not**
prove the origin of a white flash on another machine. Hyprland 0.56.2's upstream
default clear color is dark, and the theme's root is dark as well. A greeter/VT
handoff, driver issue, previous wallpaper buffer or autostarted fullscreen client
requires the physical machine's evidence. Do not classify a fullscreen window as
white from its class or state alone. The original login theme remains visible
until SDDM closes its view; the theme does not add an authentication-success hide
animation or attempt to delay SDDM/UWSM.

To apply these configuration changes to an already prepared Debian PC:

```bash
cd ~/hyprixe-debian
git pull
./install.sh native --no-packages
./verify.sh --dependencies
# Save your work, then reboot so SDDM rereads InputMethod.
sudo reboot
```

Use `./install.sh native` if dependencies need installation. At SDDM, confirm that
clicking the password field no longer opens a virtual keyboard; type normally,
then select **Hyprland (uwsm-managed)** and log in. Inside that session:

```bash
cd ~/hyprixe-debian
./verify.sh --dependencies --session
./verify.sh --session --diagnostics
```

`--session` checks loaded unit ordering and monotonic activation times. Completion
of the wallpaper request before service activation is checked; this is not proof
that a particular frame reached the monitor. A later manual wallpaper-service
restart makes the original chronology **SKIPPED**, rather than a false failure.

`--diagnostics` is read-only: SDDM and user journals, UWSM/unit state and timings,
the critical chain, current client classes/fullscreen flags, layers, awww IPC and
XDG autostart program names. It never restarts SDDM, starts/stops services, kills
windows or uses sudo. Window titles, full command arguments and complete process
environments are not included in the diagnostic report. Bind command arguments
are also omitted. A snapshot cannot identify a transient window
that disappeared before collection. If system journal access is restricted, run
the SDDM query explicitly:

```bash
sudo journalctl -b -u sddm --no-pager -o short-monotonic
journalctl --user -b --no-pager -o short-monotonic
systemctl --user status graphical-session.target hyprixe-session.target \
  hyprixe-awww.service hyprixe-wallpaper.service waybar.service --no-pager
```

Run diagnostics just after an affected login and note whether the flash covered
the whole display or a client window, and approximately when/how long it appeared.
The absence of a visible flash, actual keyboard behavior, PAM authentication and
GPU/VT transition still require observation on the physical PC.

### Other component diagnostics

- Startup/finalization log: `~/.local/state/hyprixe/session.log`.
  Managed services log to the user journal, for example
  `journalctl --user -b -u waybar.service -u hyprixe-awww.service -u hyprixe-wallpaper.service`.
  `wallpaper.log` is used only by the standalone wallpaper helper's fallback.
- Active scripts never kill an awww daemon. The wait of up to 5 seconds is
  for IPC and output readiness, not a fixed startup delay.
  Hotplug only reapplies the image.
- Keep one Waybar/Hypridle instance and one wallpaper daemon. The session target
  reuses the vendor services, so enabled units do not cause duplicate instances.
  Remove separate manual copies from personal autostart configuration when migrating.
- If Waybar reports `result=dependency`, check the selected SDDM session,
  `uwsm check is-active -v compositor-only` and `graphical-session.target` first.
  A populated systemd environment alone does not prove that its graphical
  session target is active. Use the managed session instead of altering dependencies.
- The native profile does not force any NVIDIA/Intel/AMD driver. Install the
  appropriate GPU driver; check DRM and acceleration before attributing a
  rendering issue to the theme.
- Alt+Tab cycles through windows on the current workspace. Alt+F10 shows all
  windows in Rofi. Cycling follows stable creation-ID order on that workspace;
  confirm a selection in the graphical switcher with Enter.
  Run `./verify.sh --dependencies --session` inside the affected session to check
  all 67 actual bindings and enabled Lua handles, root submap, modifiers,
  duplicates, installed script permissions, command dependencies and dispatcher
  constructors. Only a no-op is dispatched by this check. Use left Alt rather
  than French AltGr, and open at least two windows on one workspace for cycling.
  See [docs/KEYBINDS.md](docs/KEYBINDS.md) for the complete contract, application
  commands and diagnostic procedure. Physical input and focus effects still
  require testing on the PC.
- The `extras/kooldots` library contains generic examples that have not been
  fully ported to this reduced configuration. Its update tools, themes,
  Fedora/Ubuntu repair tools and SSH scripts are never run or installed.
- `./verify.sh` reports **SKIPPED** for unavailable graphical checks.
  The validations actually performed are recorded in [docs/VALIDATION.md](docs/VALIDATION.md).
- The verifier prepends `~/.local/bin` to PATH, just like the installer and
  Hyprland, and the dependency report lists the selected Rofi/Waybar/awww paths.
  A terminal outside Hyprland can therefore find the installed user binaries.
  An X11-only Rofi is reported as an incompatible runtime; its display-connection
  errors are not presented as six separate theme errors.
- ShellCheck and Lua validation tools are optional. Install them with
  `sudo apt install shellcheck lua5.4` to run those checks. Running the verifier
  as your desktop user is correct; the root-only test fixture may remain SKIPPED.

The tracked `hypr/waybar/style.css` is a regular CSS file containing a relative
import. It must not be a symbolic link whose target is CSS text. Source checks
include dangling symlinks before filtering readable files, and a broken source
tree fails validation before deployment tests run. Git attributes preserve the
exact original bytes of the two Frosted Glass Kvantum files; their SHA256 checks
do not depend on the checkout platform or line-ending settings. The Dolphin
toolbar and preferences match their pre-9259fa5 Git hashes; the toolbar retains
its inherited CRLF format and attribution. The Dolphin-specific paint variant
is checked separately and does not replace the original global theme pair.

Primary references: [Hyprland Lua 0.56.2](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua),
[Debian backports package](https://packages.debian.org/source/trixie-backports/hyprland),
[Debian backports instructions](https://backports.debian.org/Instructions/),
[Qt/KDE in Debian 13](https://wiki.debian.org/PkgQtKde/TrixieReleasePlans),
[Kvantum Qt6](https://packages.debian.org/trixie/qt6-style-kvantum),
[KXMLGUI6 retains kxmlgui5](https://github.com/KDE/kxmlgui/blob/v6.13.0/src/kxmlguiclient.cpp),
[building Rofi](https://github.com/davatorium/rofi/blob/2.0.0/INSTALL.md).

Session references: [Hyprland's UWSM integration](https://wiki.hypr.land/Useful-Utilities/Systemd-start/)
and [UWSM session/application management](https://github.com/Vladimir-csp/uwsm).
