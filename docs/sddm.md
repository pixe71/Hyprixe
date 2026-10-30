# SDDM Frosted Glass

[Documentation index](README.md)

Hyprixe supplies its own Qt 6 QML greeter under
[sddm/themes/hyprixe-frosted](../sddm/themes/hyprixe-frosted). It uses the forest
wallpaper, a rounded translucent panel, clock/date, user/avatar selection,
password field, session chooser and power controls. Layouts adapt to available
space rather than a fixed 1920×1080 coordinate grid. Physical HiDPI rendering,
PAM authentication and the transition into Hyprland remain manual checks.

SDDM is a separate greeter environment: its Qt effects are not Hyprland's
desktop blur. The theme does not change UWSM or the Hyprland session entry.

## Installation and configuration

The full installer requires SDDM with `sddm-greeter-qt6` already available, then
installs the QML runtime modules from [packages-sddm.txt](../packages-sddm.txt).
It uses sudo only for the system transaction.

| System path | Purpose |
| --- | --- |
| `/usr/share/sddm/themes/hyprixe-frosted/` | Theme files and a copy of the existing wallpaper readable by the greeter |
| `/etc/sddm.conf.d/zz-hyprixe-theme.conf` | Managed theme directory/name and input-method settings |
| `/var/lib/hyprixe/sddm/backups/` | Private, dated system-file backups and manifests |

The effective managed settings are:

```ini
[Theme]
Current=hyprixe-frosted
ThemeDir=/usr/share/sddm/themes

[General]
InputMethod=
```

Empty `InputMethod` disables Qt's virtual keyboard. The theme does not
instantiate an `InputPanel` or force a virtual-keyboard component. Focusing
the password field should use the physical keyboard normally.

SDDM reads `/etc/sddm.conf` after snippets. When a higher-priority local file
overrides the managed keys, the installer backs it up and removes only those
conflicting keys. Unrelated settings and other themes remain. It rejects a
session directory configuration that excludes Debian's Wayland session entry.

The session chooser remains available. Select **Hyprland (uwsm-managed)**;
Hyprixe neither forces plain Hyprland nor rewrites its `.desktop` file.
SDDM is not restarted by installation. Save work and reboot to refresh the
greeter safely after initial installation or a greeter change.

## Verification

```bash
./verify.sh --sddm
./verify.sh --dependencies --session
sudo journalctl -b -u sddm --no-pager
```

Source/installed-file checks cover required QML, theme configuration,
wallpaper, input method and preserved UWSM session availability. Native QML
checks run when the necessary tools exist. None of these checks proves a real
password login, scaling or absence of a white transition on the physical PC.

## Restore only the greeter

Use a working TTY if the greeter is unusable. Run from the checkout as your
normal sudo-enabled user:

```bash
./uninstall.sh --sddm-only --list
./uninstall.sh --sddm-only --dry-run
./uninstall.sh --sddm-only
```

To select another system transaction, add `--backup=SYSTEM_BACKUP_ID` from that
list. The restore returns previous settings/files and removes only files the
transaction introduced, with conflict checks. It does not uninstall SDDM.
Reboot after saving work. A normal linked full restore can also cover SDDM;
see [restore](uninstall-restore.md) before mixing separate and full transactions.
