# Uninstall and restore

[Documentation index](README.md)

Hyprixe uninstallation is **transaction restoration**, not recursive deletion
of your configuration directories. Use the backup associated with the change
you want to undo; inspect later transactions before restoring an older one.

## User backups

Backups live under
`${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe/backups/`. The dated manifests
record managed files, original contents/modes/file symlinks, created paths,
profile and any linked system-theme/account-shell state. Unchanged repeat
installs need no additional backup.

```bash
./uninstall.sh --list
./uninstall.sh --backup=BACKUP_ID --dry-run
./uninstall.sh --backup=BACKUP_ID
```

Without `--backup`, restore selects the most recent unrestored transaction.
`--dry-run` previews without applying. Run as the original normal user, not
root; linked system restoration requests sudo when needed.

The restorer validates the backup and current managed targets before writing.
It restores replaced originals, removes files newly introduced by that
transaction and retains unrelated personal files. A changed managed file or
corrupt backup stops the restore before partial changes. Preserve your edits
and inspect the conflict; there is no generic force-overwrite flag.

## What is covered

- User configuration/assets and locally installed runtime files recorded in
  that transaction, including `.zshrc` and `.p10k.zsh` for full shell deployments.
- The prior login shell when the manifest records a shell change. The account,
  expected current shell and original shell validity are checked; a different
  manually selected third shell blocks restoration.
- SDDM files/settings when a system backup is linked to the user transaction.
  Both sides are preflighted before restoration begins.
- Scoped Waybar or Dolphin changes when their specific transaction is selected.

Not covered: uninstalling Debian packages, removing the APT backports source,
rolling back every package upgrade, deleting personal history/cache, or restoring
arbitrary unrecorded files. Bash remains installed. Generated shell caches and
unrelated files are not recursively erased.

## Dolphin changes after installation

Current paint-only Dolphin transactions merge the old colour selection back
while preserving unrelated interface changes. Legacy full backups can conflict
when Dolphin has saved managed settings after installation. The narrowly scoped
`--save-dolphin-changes` option preserves those changed Dolphin files/view
metadata before restoring their originals:

```bash
# Close Dolphin first; review the selected transaction.
./uninstall.sh --backup=BACKUP_ID --save-dolphin-changes --dry-run
./uninstall.sh --backup=BACKUP_ID --save-dolphin-changes
```

It does not permit overwriting changed Kitty, Rofi or other application files.
See [Dolphin recovery](dolphin-kvantum.md) for the separate one-time layout rollback.

## SDDM-only recovery

System backups are private under `/var/lib/hyprixe/sddm/backups/`; their IDs
are separate from user-backup IDs. From a TTY or other working session:

```bash
./uninstall.sh --sddm-only --list
./uninstall.sh --sddm-only --backup=SYSTEM_BACKUP_ID --dry-run
./uninstall.sh --sddm-only --backup=SYSTEM_BACKUP_ID
```

The previous theme settings and any affected local configuration are restored;
other themes and the UWSM session files are not deleted. Read the selected
manifest before mixing an SDDM-only recovery with a full linked restore.

## Activate the restored state

Reconnect after restoring login-shell or session/environment files; reboot
after restoring greeter settings. For scoped Waybar restoration, restart its
service. A Lua-only rollback can use `hyprctl reload` and `hyprctl configerrors`.
Keep backups until the restored desktop has been checked interactively.
