# NixOS profile · Hyprixe desktop and SDDM

The NixOS profile is planned. It integrates the Hyprland session, desktop
and per-user theming on the pinned NixOS 26.05 and Home Manager 26.05 inputs.
Debian 13 remains the supported Hyprixe desktop.

## Install from an external flake

The [installation guide](../../docs/nixos-installation.md) covers both an
existing Flake and a traditional NixOS configuration wrapped in a small
Flake. Use the complete local source while the profile is under development.
The tested target is NixOS 26.05 with Home Manager release-26.05 and
`x86_64-linux`.

The root flake exports `nixosModules.default` and `homeManagerModules.default`.
Each module declares `programs.hyprixe.enable` in its own scope, disabled by
default. The NixOS module enables the official Hyprland module with UWSM. The
official module supplies the compositor, portals, polkit and session entries.
Hyprixe declares the Hyprlock PAM service on the system. The NixOS
`programs.hyprlock` module also enables Hypridle, so leave it disabled when
Hyprixe owns the session.
The Home Manager module links `hyprland.lua`, `profile.lua` and the canonical
`lua/` and `UserConfigs/` modules under `$XDG_CONFIG_HOME/hypr/`.

Hardware, boot configuration, networking, display manager and account setup
stay under host control. Add the Home Manager module only to the accounts
that should use Hyprixe. Each account has its own home configuration,
wallpaper, palette, clipboard history, caches and user systemd manager.
Simultaneous graphical sessions and multi-seat are unverified.

The desktop uses the Core's French AZERTY default in
`hypr/UserConfigs/user_settings.lua`. Configure a different desktop layout
using the host's Home Manager override for that file. The greeter keyboard
layout comes from the host.

## Public options

| Scope | Option | Default |
| --- | --- | --- |
| NixOS | `programs.hyprixe.enable` | `false` |
| Home Manager | `programs.hyprixe.enable` | `false` |
| NixOS | `programs.hyprixe.sddm.enable` | `false` |
| NixOS | `programs.hyprixe.sddm.sync.enable` | `false` |
| NixOS | `programs.hyprixe.sddm.sync.users` | `[]` |

The theme option requires the host's native SDDM service. Synchronization
requires the theme and at least one declared local normal account. A greeter
can remain enabled independently of the desktop. Home Manager packages the
publisher only for enrolled accounts when synchronization is enabled.

## Session and existing files

Select **Hyprland (uwsm-managed)** in the display manager. An SDDM host can set
`services.displayManager.defaultSession = "hyprland-uwsm";` in its own
configuration. From a text login, the same session can be started with
`uwsm start -e -D Hyprland hyprland.desktop`. Hyprixe leaves display manager
selection and configuration to the host.

The Core startup callback runs `SessionStartup.sh`. The NixOS build supplies
its Bash interpreter and command paths. The script finalizes UWSM once and
queues `hyprixe-session.target`. UWSM activates `graphical-session.target`.
The Hyprixe target is ordered after it and stops with it. The rendered target
starts `hyprixe-wallpaper.service`, `waybar.service`, `hypridle.service`,
`swaync.service`, `hyprixe-polkit.service` and `hyprixe-clipboard.service`.
The wallpaper unit is bound to `hyprixe-awww.service`. It restores the wallpaper
and publishes the palette before the other units start. All units stop with
the graphical session. The wallpaper script reapplies the selected image
after monitor changes while the session service is active. The daemon also
starts the restore unit after automatic recovery, so an awww crash does not
require the user to log in again.

The session inherits the login and compositor environment through UWSM. The
Core exports the toolkit settings in Lua. Dolphin receives its own Qt style
and plugin paths from its wrapper. A UWSM bootstrap exposes custom XDG
config, data, cache and state directories. Home Manager exposes the same unit
files in the default search directory when the config directory differs.

Keep the Home Manager `wayland.windowManager.hyprland` module disabled with
Hyprixe. Review any existing Hyprland files before activation. Home Manager
reports collisions with real files at managed destinations. Move or adopt
them explicitly, and remove conflicting declarative entries or a
`HYPRLAND_CONFIG` override from the launcher environment. User overrides can
be supplied by replacing individual `xdg.configFile` sources in the host
configuration. Leave competing Home Manager modules for Hyprland, Waybar,
Kitty, Hyprlock, Hypridle, SwayNC, Cliphist and Zsh disabled in this account.
Keep additional Polkit agents out of the session. If the host supplies
Hyprland itself, Home Manager requires UWSM and the Hyprlock PAM service.
The Home Manager Rofi module can keep its configuration under `rofi/`.
Hyprixe's launchers select the packaged patched Rofi and their own files
under `hypr/rofi/` by absolute executable path.

For session diagnostics, use `systemctl --user status graphical-session.target
hyprixe-session.target` and `journalctl --user -b -u hyprixe-wallpaper.service
-u waybar.service`. After repairing an unusable theme cache, restart Waybar
and SwayNC if they started with the packaged fallback stylesheet.

## Desktop applications

- **Waybar 0.16.0** uses the stable Nixpkgs recipe and a fixed upstream source
  hash. Its native Lua IPC, taskbar and click drawer are enabled. The local
  patch preserves the Hyprixe backlight scroll floor and demotes the expected
  no-device diagnostic. With no screen backlight at startup, a config derived
  from the same JSON omits the brightness indicator, including on machines
  where Waybar detects keyboard LEDs. The central distribution glyph uses NixOS and
  Symbols Nerd Font Mono. The power button opens the shared Wlogout menu and
  the idle control toggles presentation mode. External network, Bluetooth
  and audio click actions are deferred. Hardware
  and sound indicators depend on the devices and sound service on the host.
- **Rofi 2.0.0** uses a private build with the canonical launcher patch.
  `Super+Space` opens the shared Frosted Glass launcher. The window switcher
  and terminal actions remain available. The sidebar also launches Dolphin.
  The Nix build waits for running image workers before freeing their data on
  exit.
- **Kitty 0.49.1** uses the canonical config with a resolved palette include.
  `Super+Return` launches Kitty in a UWSM scope. Home Manager supplies JetBrains
  Mono, Nerd Fonts Symbols Only 3.4.0, FontAwesome 4.7 and Breeze icons.
- **awww 0.12.1** runs in the session's foreground daemon unit. The wallpaper
  service calls the Core engine to restore the selection. The bundled
  `min_forest.jpg` is checked and decoded at build time.

### User applications

| Shortcut or command | Application and integration |
| --- | --- |
| `Super+L` | Hyprlock 0.9.5 uses system PAM, the current Hyprixe wallpaper and the lock colours. |
| Idle and logind events | Hypridle 0.1.7 uses the Core 600/720 second timers, logind and Hyprland DPMS. |
| `swaync-client -t` | SwayNC 0.12.6 toggles the notification centre. Standard `notify-send` works over D-Bus. |
| `Super+Backspace` or Waybar power button | Wlogout 1.2.2 uses the canonical `hyprixe-session` helper. Logout uses UWSM. Shutdown and reboot require confirmation and go through systemd authorization. |
| `Super+E` or Rofi folder button | Dolphin 26.04.3 uses Qt 6, Kvantum 1.1.7, Breeze icons, KIO workers and thumbnail plugins. Mounting removable storage depends on the host's UDisks configuration. |
| `Super+Return` | Kitty starts Zsh with the canonical prompt, Powerlevel10k 1.20.15 and packaged gitstatusd. |
| `Super+Ctrl+V` | A single `wl-paste` watcher feeds Cliphist 0.7.0. The canonical Rofi menu restores text and images. `Ctrl+Delete` deletes an entry and `Alt+Delete` clears the history. |

The KDE Polkit agent handles graphical authentication through the system bus.
Hyprlock, Wlogout and the brightness popup start on demand. SwayNC is
registered on the session bus through its single session-bound systemd unit.
Wlogout uses the pinned librsvg loader to display the Core's SVG icons.

### Personal settings

Home Manager manages the canonical `.zshrc`, `.p10k.zsh`, and both named
Kvantum themes. An existing file or a conflicting Home Manager declaration at
one of these locations needs a manual choice. Hyprixe uses the default Zsh
dotfile location and stores history under
`$XDG_STATE_HOME/hyprixe/zsh/history`. Completion and Instant Prompt use
`$XDG_CACHE_HOME`. The pinned autosuggestions and syntax-highlighting scripts
are sourced in the Core order. Powerlevel10k uses the packaged gitstatusd
and has auto-install disabled.

The host owns the account's login shell. To opt in separately, register it
with NixOS `programs.zsh.enable = true` and set the account's
`users.users.alice.shell = pkgs.zsh`. Leave the Home Manager Zsh module off
for the Hyprixe account.

Home Manager seeds missing Dolphin, KDE and Kvantum settings and the
Dolphin toolbar on activation. They remain writable under
`$XDG_CONFIG_HOME` and `$XDG_DATA_HOME`. Existing files and symlinks are
preserved, including on reactivation. Dolphin is the data-level default
for directories in Hyprland, below MIME choices in `$XDG_CONFIG_HOME`.
Home Manager manages the two Dolphin desktop and MIME files under
`$XDG_DATA_HOME/applications`. Kitty is the configured external terminal.
Dolphin's optional embedded terminal panel is omitted. The Konsole plugin
tested in the VM crashed when closing the panel. Kitty remains available as
the external terminal, as in the Debian profile. Cliphist stores its history in
`$XDG_CACHE_HOME`, and the session
helpers use `$XDG_RUNTIME_DIR` for their locks.

## Dynamic Wallpaper Theming

The profile packages **Wallust 3.5.1** from the same checksummed release archive
as Debian. Nix verifies the vendored dependencies from its Cargo lockfile.
Home Manager links the Core engine, canonical templates, reference colours
and generated fallback from the store under `$XDG_DATA_HOME/hyprixe/theme`.
The shared Python engine runs with Pillow and native validators.

The format 2 preference lives in `$XDG_STATE_HOME/hyprixe/theme.json` next to
the transaction lock. The published generation is
`$XDG_CACHE_HOME/hyprixe/theme/current`; the launcher previews the wallpaper
via `$XDG_DATA_HOME/hyprixe/current-wallpaper`. These paths are user-writable.
The bundled wallpaper is saved by its stable XDG path, which resolves to the
asset of the active generation. A legacy bundled store path is migrated when
its recorded digest matches the packaged image. Missing personal images
fall back to Frosted Glass while the saved selection is preserved.

Home Manager initializes new homes after linking their files. Existing
preferences are left to the session engine. The compositor has a packaged
colour fallback before a cache exists; the wallpaper service restores or
rebuilds the generation before Waybar starts. Rofi selects the current
palette and preview when opened. Hyprland reloads and checks its configuration,
and the engine signals Waybar and running Kitty instances to reload. SwayNC
reloads CSS over D-Bus. Hyprlock and Wlogout read the active generation when
they open and have a packaged fallback if the cache is unavailable.

```sh
hyprixe-theme status
hyprixe-theme apply /path/to/wallpaper.jpg
hyprixe-theme refresh
hyprixe-theme enable
hyprixe-theme disable
hyprixe-theme default
```

`disable` keeps the chosen wallpaper with Frosted Glass colours.
`default` selects the official wallpaper and preserves the enable preference.
`init` prepares an initial generation and `restore` is used at login and
monitor hotplug.

## Frosted Glass greeter

The host selects SDDM and the session. The greeter options are independent
of the desktop's `programs.hyprixe.enable`. The
[installation guide](../../docs/nixos-installation.md#choose-the-login-method)
shows the tested static setup.

`programs.hyprixe.sddm.enable` and `sync.enable` default to false. Enable
the theme alone for static Frosted Glass. The default wallpaper is
`min_forest.jpg`, checked against the Core manifest during the build.
The package installs the canonical QML, components and icon under the
native SDDM theme directory. SDDM uses the pinned Qt 6 Qt Declarative
modules for Quick, Basic Controls, Layouts and Effects, and Qt SVG for the icon.
JetBrains Mono is provided at system scope. The theme uses its packaged
avatar and leaves the virtual keyboard inactive. The profile uses the host's
SDDM service, session selection and authentication settings.
The graphical fixture exercises X11 for the greeter and Wayland for the
Hyprland session. The host configures its greeter keyboard layout.

### Publishing the shared greeter snapshot

For optional publication, add the following options at system scope and
replace the example name with an existing local account that uses Hyprixe.

```nix
programs.hyprixe.sddm.sync = {
  enable = true;
  users = [ "alex" ];
};
```

The socket `/run/hyprixe-sddm-sync.sock` belongs to root and the access group,
with mode `0660`. The publishing process needs the new supplementary group.
Start a fresh login after enrollment. If a user systemd manager stays active
between logins, reboot before testing publication so it starts with the new
group membership.
The receiver checks the connecting UID using `SO_PEERCRED` and the
root-owned policy at `/etc/hyprixe/sddm-sync-users.json`. The policy names
accounts so the receiver resolves their UIDs through NSS at connection time.

The receiver runs as the reserved non-interactive system account
`hyprixe-theme`. It cannot be a publisher or a normal host account.
Systemd starts it on demand and it exits after 30 seconds of inactivity.
Its sandbox hides home directories, makes the system read-only, isolates
devices, temporary files and networking, restricts sockets to Unix and
removes capabilities. Only the receiver writes `/var/lib/hyprixe/theme`.

The shared Debian/Core protocol sends one already-open descriptor with its
digest and seven semantic colours. It accepts no source or destination path.
The client checks that its descriptor still matches the digest used to
validate the wallpaper against the desktop palette.
The receiver checks ownership, size, dimensions, format, digest and contrast,
then decodes and re-encodes the image as RGB PNG. When given the official
image's exact store path, the NixOS client creates a private user-owned
temporary copy and verifies the digest before sending
the file descriptor through the same protocol. Personal images are sent
through the ordinary ownership checks.

The last valid publication by an authorized account wins. The receiver
serializes requests and atomically switches `current` to the complete
snapshot. It keeps the current and two preceding generations on disk.
The greeter reads the system snapshot at its next appearance. Snapshot
images and palettes are readable locally. They persist through logout,
reboot, rebuild and garbage collection of old Nix generations.

With synchronization enabled, the greeter loads a QML fragment generated
by the receiver. The protocol restricts publishers to validated colour
values and image descriptors. The receiver therefore remains in the
greeter's trust boundary. Keep publication disabled on machines where a
static greeter is sufficient. An inert palette format and trusted reader
would further narrow this boundary.

For enrolled Home Manager accounts, successful `apply`, `refresh`,
`default`, `enable`, `disable` and `restore` publish the resulting
wallpaper and palette. `default` republishes the official image. `status`
reads the desktop state and the Home Manager initialization leaves the
greeter snapshot alone. A rejected export emits a warning and preserves
the working desktop and last valid greeter snapshot. An empty state or
unreadable snapshot uses the packaged fallback. On a fresh dynamic boot Qt
may log that the optional `Palette.qml` is absent before any export.

Disabling `sync.enable` removes the socket, receiver and policy from the
selected generation and switches the greeter to the packaged assets.
The snapshots stay on disk and are ignored in static mode. Re-enabling
sync makes the last retained snapshot available again. Disabling
`sddm.enable` releases theme selection back to the host. Display-manager
generation changes follow the native NixOS restart policy. If the daemon
still has the previous theme selection, apply it after logout or reboot.

For diagnostics, inspect `systemctl status hyprixe-sddm-sync.socket`,
`journalctl -u hyprixe-sddm-sync.service` and `journalctl -u display-manager.service`.
Check the publisher's current group membership with `id` after logging in.
An inactive receiver with an active socket is normal between publications.

## Brightness popup

Left-click the Waybar brightness indicator to open the canonical GTK popup.
It uses PyGObject, GTK 3, GtkLayerShell and Gio D-Bus to ask logind to apply
the 5–100% slider. It closes on Escape, a second click or three seconds
outside the popup. Returning the pointer cancels the timeout, and dragging
holds it open. The popup uses the current Frosted Glass colours and runs
on demand. Waybar hides the control when no usable screen backlight is found.

## Checks

From the repository root with Nix flakes enabled, use a `path:` reference to
include new files before they are tracked by Git.

```sh
nix flake show path:.
nix flake check --no-build path:.
nix flake check path:.
sh profiles/nixos/tests/external/check.sh
nix build --no-link --no-write-lock-file --override-input hyprixe "path:$PWD" \
  "path:$PWD/profiles/nixos/tests/external#session-vm"
./verify.sh
./verify.sh --profile nixos
```

The `x86_64-linux` checks compare the disabled fixture with a host that
omits Hyprixe, build the Home Manager generations, verify the packaged UWSM
session, target dependencies and palette imports. They run the Core Lua mock,
native Rofi and Kitty parsers, and `Hyprland --verify-config` with the default
and custom XDG config layouts. The external check builds the Home Manager
generations for disabled, desktop-only, two-user, static and dynamic
configurations and evaluates their host systems. It checks diagnostics for
invalid greeter, authorization and competing desktop configuration options.
The engine check runs the existing wallpaper and brightness suites with the
pinned Wallust and GTK typelibs. The KVM test uses native SDDM to exercise
two wallpaper selections, application reloads, cache recovery, persisted
preferences and the UWSM stop and restart cycle. The same fixture exercises
PAM, Polkit, notifications, Wlogout confirmation, Dolphin with Kvantum, Zsh,
Cliphist and shortened Hypridle timers with a keyboard DPMS wake. The test
uses a disposable account and cancels poweroff and reboot at the confirmation
dialogue. The GTK brightness test uses a fixture backlight and simulated
logind replies. Physical brightness, suspension, resume and peripheral
access need testing on real hardware.
The same VM compares rendered greeter colours and wallpaper against the
official image and two personal images. It logs in through SDDM, checks
authorized concurrent publishers, a rejected publication, persistence
across reboot, and the static configuration with a retained snapshot. It also
exercises a daemon crash, switches to a second configuration inside the VM,
returns to the previous closure and disables the profile while checking that
writable settings and the greeter snapshot are preserved. The external VM
uses the same test suite with the public module exports. It starts from an
existing host configuration with Hyprixe disabled and activates a built
configuration in the guest. It checks account isolation and preservation of
an existing shell file on an activation collision. Run the graphical
test on a Linux builder with QEMU and access to KVM. Nix evaluation and the
regular checks can run on a Linux builder without KVM.
