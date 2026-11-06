# Update, verify and restore

Run from your checkout as the desktop user. Preserve local edits before pulling.

## Update

```bash
git status --short
git pull --ff-only
# Close Dolphin and finish transfers.
./install.sh native
```

Use `vmware` only for that hardware profile. `--no-packages` reuses prepared
binaries/dependencies/assets; use a normal install when any are missing.
Repeat installation backs up changed managed files and is a no-op for identical
file payloads. Debian package upgrades are separate from file idempotence.

## Activate changes

| Change | Activation after deployment |
| --- | --- |
| Lua settings/bindings | `hyprctl reload`, then `hyprctl configerrors` |
| Rofi / Wlogout | Reopen the menu |
| Waybar | Restart `waybar.service` |
| Kitty / Zsh / prompt | Open a new terminal; reconnect after account-shell changes |
| Dolphin paint | Close, deploy, reopen |
| Hypridle config | Restart `hypridle.service` |
| Session environment / user units | Full logout/login |
| SDDM / greeter settings | Save work and reboot |

Dynamic wallpaper commands already orchestrate their own colour reloads.

## Component updates

```bash
./install.sh native --waybar-only --no-packages
systemctl --user restart waybar.service
./verify.sh --waybar --session

# Close Dolphin first.
./install.sh native --dolphin-only
./verify.sh --dolphin
```

Do not use legacy interface-restoration flags during routine updates.

## Verify

```bash
./verify.sh                              # sources and isolated regressions
./verify.sh --dependencies               # also require the deployed runtime
./verify.sh --dependencies --session     # inside the Hyprland/UWSM desktop
```

A clean run ends with `RESULT: 0 failed check(s)`. `SKIPPED` means a check did
not run; it is not proof of visual or hardware success. Missing required runtime
under `--dependencies` is a failure. Source tests isolate HOME/XDG and test
configuration, deployment, theme generation, rollback, locking and restore.

Other options: `--sddm`, `--waybar`, `--dolphin`, `--session --diagnostics` and
`--profile debian`. Scoped checks do not replace the full suite. The planned
NixOS profile supports Core source checks only, not installed/session validation.
Inspect `./verify.sh --help` before combining options.

On hardware, test menus, real shortcuts, PAM unlock, audio, idle/resume, monitor
changes and logout/reboot transitions. Automated checks do not judge visual quality.

## Restore

```bash
./uninstall.sh --list
./uninstall.sh --backup=BACKUP_ID --dry-run
./uninstall.sh --backup=BACKUP_ID
```

Backups are under `${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe/backups/`.
Without an ID, the latest unrestored transaction is selected. Restore replaces
recorded managed files, removes newly introduced ones and preserves unrelated
files. Later edits or corrupt backups block restoration; preserve edits and
resolve conflicts rather than forcing an overwrite. Restore transactions in
reverse order. Linked SDDM and account-shell changes are included where recorded.

Packages/backports are not uninstalled. Mutable theme cache/preferences and
inert SDDM snapshots are retained; global XDG directories are never erased.
Reconnect/reboot after restoring session, shell or greeter settings.

From a working TTY, a separate greeter restore is available:

```bash
./uninstall.sh --sddm-only --list
./uninstall.sh --sddm-only --backup=SYSTEM_BACKUP_ID --dry-run
./uninstall.sh --sddm-only --backup=SYSTEM_BACKUP_ID
```

System backup IDs under `/var/lib/hyprixe/sddm/backups/` differ from user IDs.
Review linked transactions before mixing SDDM-only and full restores.

For legacy Dolphin backups only, `--save-dolphin-changes` preserves changed
Dolphin files before restoring their originals. A separate one-time interface
rollback uses `--dolphin-only --restore-dolphin-interface --interface-backup=ID`.
Preview and inspect the chosen backup first; neither option permits overwriting
unrelated edited applications.
