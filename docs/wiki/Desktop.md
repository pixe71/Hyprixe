# Desktop components

All components keep the Frosted Glass layout. [Dynamic Theming](Dynamic-Theming)
changes colours; its stable wallpaper link supplies previews and the lockscreen.

## Waybar

| Area | Contents |
| --- | --- |
| Left | Collapsible tray drawer, workspaces 1–4, per-window taskbar |
| Center | CPU temperature/root-storage fallback, memory, CPU, Debian logo, time/date, idle inhibitor |
| Right | Network, Bluetooth, audio, battery, power menu |

Click **☰** to open the drawer; it contains tray, music, title and submap.
The eye enables presentation mode through the idle inhibitor. Temperature is
discovered from CPU sensors, with root-storage usage as fallback. Battery uses
automatic discovery; missing battery/Bluetooth hardware is normal.

Source: `common/config/hypr/waybar/`. The service explicitly loads
`configs/Frosted-Glass` and `style.css`. See [Maintenance](Maintenance#component-updates)
for a scoped update.

## Rofi and clipboard

| Shortcut | Menu |
| --- | --- |
| `SUPER + Space` | Applications, current wallpaper and round sidebar buttons |
| `ALT + F10` | Window search with the same wallpaper shell |
| `SUPER + CTRL + V` | Compact clipboard history |

The sidebar opens Applications, Files, Windows or Terminal. Search, arrows,
Enter and Escape keep native Rofi behaviour. Clipboard deletion uses
`CTRL + Delete` for one item and `ALT + Delete` for all history.
All menus share `themes/Frosted-Glass-Common.rasi`; layout is kept separate.
The installer prepares the compatible Wayland build needed by the sidebar.

## Wlogout

`SUPER + Backspace`, `SUPER + SHIFT + E` and Waybar's power button reach the
same horizontal **Lock | Logout | Shutdown | Reboot** menu. Escape dismisses it;
exit/power actions ask for confirmation. Logout uses `uwsm stop`.
There are no Suspend/Hibernate buttons. Source: `common/config/wlogout/`.

## Kitty, Zsh and Powerlevel10k

Kitty is the default terminal. It uses the account's login shell rather than a
hardcoded shell command. Installation prepares Zsh, autosuggestions, syntax
highlighting and pinned Powerlevel10k/gitstatus/font assets before changing
that account shell. Bash scripts remain Bash.

Full-session reconnect activates an account-shell change. `p10k configure` is
optional; keep deliberate prompt edits in the repository before redeployment.
Main sources: `common/config/kitty/` and `common/shell/`.

## Dolphin and Kvantum

Dolphin uses an app-specific light glass variant. Paint-only installation
preserves personal panels, toolbar, view settings and unrelated Qt applications.
Close Dolphin and finish transfers before deployment; it is not killed for you.
The theme and KDE colour scheme must stay consistent.

Sources: `common/config/Kvantum/Frosted-Glass-Dolphin/` and
`common/local/share/color-schemes/HyprixeFrostedDolphin.colors`.
The optional maintainer generator is `tools/build-dolphin-theme.py`.
See [Maintenance](Maintenance#restore) for legacy layout recovery.

## Lock and idle

`SUPER + L` and Wlogout share a duplicate-protected Hyprlock helper. Test a real
password unlock before relying on it. Hypridle locks after 10 minutes and turns
screens off after 12 minutes; it also locks before sleep and restores display
power after resume. **There is no automatic system-suspend timer.**

Waybar's eye inhibits automatic idle behaviour, while manual locking remains
available. Sources: `common/config/hypr/hyprlock.conf` and `hypridle.conf`.

## SDDM and the session

SDDM uses the shared Qt 6 theme, a system wallpaper/palette copy and bundled
fallback. Always select **Hyprland (uwsm-managed)**. The installer manages:

- `/usr/share/sddm/themes/hyprixe-frosted/` — static QML/theme resources.
- `/etc/sddm.conf.d/zz-hyprixe-theme.conf` — theme selection and empty `InputMethod`.
- `/var/lib/hyprixe/theme/current/` — dynamic greeter snapshot.

UWSM owns the compositor environment and `graphical-session.target`.
`hyprixe-session.target` orders awww/wallpaper before the desktop services;
clipboard, Waybar, SwayNC and idle services follow that lifecycle. Do not start
second daemons from ad-hoc autostart entries. The wallpaper oneshot being
`active (exited)` is normal. See [Architecture](Architecture) and [Troubleshooting](Troubleshooting).
