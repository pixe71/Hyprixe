# Installing Hyprixe Debian

## Prerequisites

- Debian GNU/Linux **13 (trixie)**, a regular user account, access to `sudo`,
  a network connection and several GB of free space for APT and the first builds.
- DRM/Mesa or NVIDIA drivers suitable for the hardware, and a working
  logind/DBus session. This repository does not install proprietary drivers
  automatically.
- An existing display manager, or a local console from which to start Hyprland.
  SDDM is supported: select **Hyprland (uwsm-managed)** after installation.
  The script does not replace your display manager or configure autologin.
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

Close Dolphin, Alacritty and configuration editors to prevent them from
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
only APT commands use `sudo`. If the executable bits were lost when copying
the repository, run `chmod +x install.sh uninstall.sh verify.sh scripts/build-runtime.sh`.

The `--dry-run` mode shows which paths would change, without running APT or
copying files. It does not guarantee that dependencies are already installed.
`--no-packages` checks commands, the Hyprland version, Rofi's Wayland backend
and the Qt6 Kvantum plugin; it fails before touching configuration files if
any requirement is missing.

Use the normal `./install.sh native` command to repair missing awww or an
incompatible Rofi/Waybar. `--no-packages` also skips runtime builds; it cannot
prepare those missing capabilities. The installer reuses suitable binaries
already present in `~/.local/bin` and builds only what is missing or incompatible.

## Dependencies and system changes

`packages.txt` lists the Debian stable applications actually used.
`packages-backports.txt` lists Hyprland, UWSM, Hyprlock, Hypridle, XWayland and the
Hyprland portal. `packages-optional.txt` is optional. The VMware profile
also installs the packages in `profiles/vmware/packages.txt`.

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

The installer copies files from `.config/`, the toolbar under
`.local/share/kxmlgui5/dolphin/` and the wallpaper to
`~/.local/share/hyprixe/wallpapers/min_forest.jpg`. It never copies `extras/`.
It selects `profile.lua` and `profile.env` from the requested profile.

The relevant values in `mimeapps.list`, `kdeglobals` and `qt6ct.conf` are
merged: other MIME associations, groups and preferences are preserved.
The session-specific `hyprland-mimeapps.list` also receives the directory
association so an older session-specific choice cannot take priority.
Dolphin becomes the application for `inode/directory`. Alacritty is the
terminal for Hyprland, Rofi and KDE. Qt Widgets uses Kvantum; Qt Quick uses Basic.
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
To return to the state before several installations, undo transactions from
newest to oldest; do not delete intermediate backups. An interrupted restore
can be run again.

APT packages and the backports repository are not removed automatically.
They may be used by other applications; manage their removal separately with
APT. Log out and back in after restoring or changing profiles.

## First launch

Log out completely and select **Hyprland (uwsm-managed)** in SDDM, then log in.
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

Lua modules are loaded explicitly. To reload after an edit:

```bash
hyprctl reload
hyprctl configerrors
```

Environment/profile changes and the Hyprlang → Lua transition require
a new session, even if reloading reports no errors.

## Checking components

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
alacritty
dolphin
~/.config/hypr/scripts/RofiLauncher.sh
xdg-mime query default inode/directory
```

Alacritty, Dolphin, the Rofi launcher and Hyprlock use `uwsm app --`, as
recommended for applications in a systemd-managed compositor session.
Rofi's `run-command` also prefixes selected applications with `uwsm app --`.
The keyboard combinations and applications are unchanged. Short control
commands such as focus, volume and brightness remain direct commands.
The power menu's logout action calls `uwsm stop` for ordered session teardown.

If XDG_CONFIG_HOME is customized, replace `~/.config` in these manual commands.
Session scripts already use the XDG variables.

Hyprlock reads the same image as awww, directly from the data directory:
it does not depend on a cache generated during startup. Test locking and
unlocking before using suspend. Hypridle locks after 10 minutes and turns
outputs off after 12 minutes. There is no automatic suspend; Waybar's idle
inhibitor can pause idle handling.

Dolphin retains the minimal toolbar, Places/InformationPanel settings and
preview plugins. `F9` shows Places, `F11` Information, and `F12` previews.
On the first KDE launch without an existing window state, show the information
panel with F11 if needed: no binary VM window-geometry state is distributed.
Dolphin's embedded terminal panel depends on the optional KonsolePart;
the “open terminal” command uses Alacritty.

## Troubleshooting and limitations

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
  windows in Rofi. Cycling follows Hyprland's current-workspace order;
  confirm a selection in the graphical switcher with Enter.
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
exact original bytes of the two Frosted Glass Kvantum files and Dolphin toolbar;
their SHA256 checks do not depend on the checkout platform or line-ending settings.

Primary references: [Hyprland Lua 0.56.2](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua),
[Debian backports package](https://packages.debian.org/source/trixie-backports/hyprland),
[Debian backports instructions](https://backports.debian.org/Instructions/),
[Qt/KDE in Debian 13](https://wiki.debian.org/PkgQtKde/TrixieReleasePlans),
[Kvantum Qt6](https://packages.debian.org/trixie/qt6-style-kvantum),
[KXMLGUI6 retains kxmlgui5](https://github.com/KDE/kxmlgui/blob/v6.13.0/src/kxmlguiclient.cpp),
[building Rofi](https://github.com/davatorium/rofi/blob/2.0.0/INSTALL.md).

Session references: [Hyprland's UWSM integration](https://wiki.hypr.land/Useful-Utilities/Systemd-start/)
and [UWSM session/application management](https://github.com/Vladimir-csp/uwsm).
