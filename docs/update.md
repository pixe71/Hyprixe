# Updating

[Documentation index](README.md)

The repository is the source of truth. Commit or otherwise preserve local
customizations before pulling; `--ff-only` stops instead of creating an
unexpected merge. Review changes, particularly package, shell and SDDM changes.

```bash
cd ~/hyprixe-debian
git status --short
git pull --ff-only
# Close Dolphin and finish file operations before a full deployment.
./install.sh native
```

Keep using `vmware` instead of `native` only if you intentionally use that
profile. Normal full installation can install dependencies and prepare newly
required compatibility assets. `--no-packages` is appropriate only when all
dependencies and verified cached/installed shell assets already exist.

## Activate changes

| Changed component | Activation |
| --- | --- |
| Lua settings/bindings only | Deploy, then `hyprctl reload`; inspect `hyprctl configerrors` |
| Waybar JSON/CSS/helper | Scoped deployment, then restart `waybar.service` |
| Rofi / Wlogout config | Deploy; close and reopen the menu |
| Kitty / Zsh / prompt | New Kitty window; reconnect the desktop after an account-shell change |
| Dolphin paint | Close Dolphin, deploy scoped paint, reopen Dolphin |
| Hypridle config | Deploy and restart `hypridle.service` |
| Session environment, UWSM startup or user units | Full logout/login; daemon-reload alone cannot replace an inherited environment |
| SDDM / greeter input method | Save work and reboot to refresh the greeter safely |

After a full update affecting session or shell settings, log out and select
**Hyprland (uwsm-managed)** again. A compositor reload is not a substitute.
Then run:

```bash
./verify.sh --dependencies --session
```

## Component-only updates

Waybar uses existing dependencies and units, with no package installation:

```bash
./install.sh native --waybar-only --no-packages
systemctl --user restart waybar.service
systemctl --user status waybar.service --no-pager
./verify.sh --waybar --session
```

Dolphin's paint-only installer preserves the accepted interface:

```bash
# Close Dolphin first.
./install.sh native --dolphin-only
./verify.sh --dolphin
```

Do not add the legacy `--restore-dolphin-interface` option to routine updates.
Use it only for the specific recovery described in the [Dolphin guide](dolphin-kvantum.md).

Every modifying deployment records a dated transaction. Inspect it before
rolling back; restoring a backup from before several intervening updates can
conflict with their newer files. See [restore](uninstall-restore.md).
