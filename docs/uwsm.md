# UWSM and session services

[Documentation index](README.md)

## Why UWSM is required

UWSM manages the lifetime of Hyprland and the graphical user session through
systemd. It supplies application scopes, environment propagation and cleanup
when logging out. Hyprixe uses that lifecycle rather than treating each desktop
program as an unrelated startup process.

Select **Hyprland (uwsm-managed)** in SDDM. Debian supplies
`/usr/share/wayland-sessions/hyprland-uwsm.desktop`; the installer checks it and
does not rewrite it. The plain entry can launch a functioning compositor while
leaving `graphical-session.target` inactive, which prevents session services
such as Debian's Waybar from starting.

## Startup sequence

1. SDDM starts the UWSM session entry; UWSM launches Hyprland.
2. Hyprland loads the Lua configuration, native/profile environment and bindings.
3. [SessionStartup.sh](../common/config/hypr/scripts/SessionStartup.sh) verifies that
   UWSM manages the compositor, reloads user units and calls `uwsm finalize`
   with the compositor's display, PATH, terminal and Qt environment.
4. UWSM activates `graphical-session.target`. Hyprixe queues
   `hyprixe-session.target` without blocking compositor startup.
5. Wallpaper readiness is ordered before Waybar, SwayNC and the other desktop
   services. Those services are tied to the graphical session's lifetime.

Hyprixe never manually starts `graphical-session.target` and retains the
vendor Waybar service's session dependencies. Importing `WAYLAND_DISPLAY`
alone cannot repair a compositor launched outside UWSM.

## Services

The source units and drop-ins are under
[.config/systemd/user](../common/config/systemd/user).

| Unit | Role / expected state after login |
| --- | --- |
| `hyprixe-session.target` | Groups the desktop services; active |
| `hyprixe-awww.service` | Owns awww-daemon; running, restarted on failure |
| `hyprixe-wallpaper.service` | Applies the image to detected outputs; oneshot `active (exited)` |
| `waybar.service` | Vendor service with explicit Hyprixe config/style; running |
| `swaync.service` | Vendor notification service; running |
| `hypridle.service` | Vendor idle service with explicit config; running |
| `hyprixe-clipboard.service` | wl-paste watchers feeding cliphist; running |
| `hyprixe-polkit.service` | Desktop authentication agent; can yield to an already running agent |

Units read UWSM's session environment file. `QT_STYLE_OVERRIDE=kvantum`,
`TERMINAL=kitty`, local executable precedence and Wayland variables reach
systemd-launched applications. The setup does not install a separate custom
SwayNC theme; notifications use the installed SwayNC configuration with the
existing compositor layer integration.

## Wallpaper and login transition

The source image is [wallpapers/min_forest.jpg](../common/wallpapers/min_forest.jpg),
deployed under `$XDG_DATA_HOME/hyprixe/wallpapers/min_forest.jpg`.
[WallpaperDaemon.sh](../common/config/hypr/scripts/WallpaperDaemon.sh) owns the daemon;
[Wallpaper.sh](../common/config/hypr/scripts/Wallpaper.sh) waits within a bounded
readiness check, reuses the daemon and applies the image without an initial
fade. It detects outputs dynamically; monitor changes can reapply the wallpaper.
Hyprlock and Rofi use the same installed asset. SDDM needs its own system-readable
installed copy because the greeter cannot depend on access to a private HOME.

The wallpaper service requires awww and is ordered before the other desktop
services. This reduces late background setup; it is not proof that every GPU
shows a perfectly seamless first frame. Diagnose a white transition using
timestamps, clients and layers before adding any delay.

## Application launch and logout

The terminal and file-manager helpers use `uwsm app -- kitty` and
`uwsm app -- dolphin`. The main Rofi launcher uses a UWSM application scope.
Clipboard/window-selector Rofi processes retain their existing input/output
pipeline in the managed session environment. Wlogout uses a named transient
UWSM service so its second invocation can stop that menu alone.

Confirmed Wlogout Logout calls **`uwsm stop`**, allowing UWSM/systemd to shut
down the compositor and session services. It does not kill Hyprland directly.

## Diagnostics

Run inside the intended session:

```bash
uwsm check is-active -v compositor-only
systemctl --user is-active graphical-session.target hyprixe-session.target
systemctl --user show-environment | grep -E '^(WAYLAND_DISPLAY|HYPRLAND_INSTANCE_SIGNATURE|XDG_CURRENT_DESKTOP|QT_STYLE_OVERRIDE|TERMINAL)='
systemctl --user status waybar.service hyprixe-awww.service hyprixe-wallpaper.service --no-pager
journalctl --user -b -u hyprixe-wallpaper.service -u waybar.service --no-pager
./verify.sh --dependencies --session
```

The startup helper also logs to
`${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe/session.log`.
See [troubleshooting](troubleshooting.md) for failed targets and login transitions.

Primary background: [UWSM upstream](https://github.com/Vladimir-csp/uwsm) and
[Hyprland's UWSM guidance](https://wiki.hypr.land/useful-utilities/uwsm/).
Use Hyprixe's Debian package procedure rather than another distribution's
installation commands from those references.
