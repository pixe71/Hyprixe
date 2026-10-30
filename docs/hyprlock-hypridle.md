# Hyprlock and Hypridle

[Documentation index](README.md)

## Manual locking

`SUPER + L` and Wlogout's Lock action share
[LockScreen.sh](../.config/hypr/scripts/LockScreen.sh). It guards against
duplicate instances and launches Hyprlock through UWSM with the explicit
[hyprlock.conf](../.config/hypr/hyprlock.conf).

Hyprlock uses the same installed forest wallpaper, its own configured blur,
Frosted Glass colours and a password/error display. No forced software-rendering
variables are required by the native profile. The optional VMware profile
keeps its isolated graphics adaptations.

Test locking and unlocking with your account password on the actual PC. Parser
and dependency checks cannot certify PAM authentication or recovery from sleep.

## Idle and display power

[hypridle.conf](../.config/hypr/hypridle.conf) is the source of truth for timers
and actions. The shipped configuration requests session locking through
`loginctl` on idle, then turns displays off through Hyprland DPMS at a later
timeout. It also requests a lock before sleep and restores display power after
resume. **No automatic system-suspend timer is configured.**

`hypridle.service` is started as part of the UWSM graphical session, with a
drop-in pointing at the installed config. It is not a separately spawned second
idle daemon.

Waybar's eye toggles the native idle inhibitor. When active it is presentation
mode, inhibiting automatic idle behaviour; it does not disable `SUPER + L`,
remove the lock screen or replace system-wide power policy. Do not infer that
it prevents every explicit suspend request from other programs.

## Checks

```bash
systemctl --user status hypridle.service --no-pager
journalctl --user -b -u hypridle.service --no-pager
./verify.sh --dependencies --session
```

In a safe interactive test, press `SUPER + L`, unlock, then test idle and
resume with and without the Waybar eye enabled. Exact timeout values should be
read from the configuration before changing them in the repository. Deploy
and restart `hypridle.service` after an idle-config edit.
