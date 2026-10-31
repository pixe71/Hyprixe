# Installation

[Documentation index](README.md) · [Requirements](requirements.md)

The root installer delegates to `profiles/debian/install/` and consumes the
canonical sources in `common/`. This internal layout does not change user
paths, transaction format or public commands. `native`/`vmware` select hardware
adaptations within Debian; they are not OS profiles. NixOS is planned only.

## Prepare Debian

Use Debian 13 Trixie with a normal sudo-enabled desktop account, Python 3, Git,
and SDDM's Qt 6 greeter. The installer refuses root and other OS/version targets.
Read [requirements](requirements.md) before running it on a fresh system.
Close Dolphin and finish file transfers before a full deployment; it is never
killed automatically. Keep a TTY or other working session available.

```bash
git clone https://github.com/pixe71/hyprixe-debian.git
cd hyprixe-debian
./install.sh native
```

`./install.sh` is equivalent to `./install.sh native`. Sudo is requested for
APT, system SDDM files and the final account-shell change. Do not run the whole
installer with sudo. Read its errors before retrying; a failed critical step
returns a nonzero exit code.

## What a full installation does

1. Check Debian, the invoking account, paths, SDDM and configuration safety.
2. Configure official `trixie-backports` if absent; install stable packages and
   select backports for the Hyprland ecosystem. Build compatible awww/Waybar/Rofi
   binaries when the installed ones lack required capabilities.
3. Stage and verify pinned Powerlevel10k, gitstatus and Nerd symbol-font assets;
   check runtime dependencies before deploying user configuration.
4. Create dated backups, copy managed configuration and wallpaper, render XDG
   paths and install user services. Existing Dolphin interface settings are
   preserved; only its native colour-scheme setting is merged.
5. Install the SDDM theme with a separate linked system backup, refresh font
   caches and test the Zsh startup and prompt assets.
6. Display the account-shell change and set that user's login shell to a verified
   Zsh executable in `/etc/shells`, only after those checks succeed.

Installation is designed for repeats: unchanged managed files need no new
transaction. It is not a promise of a full system rollback for APT or build
failures. Debian package changes and the backports source remain installed.
User-file and SDDM restoration are described in [restore](uninstall-restore.md).

## Profiles and options

```bash
./install.sh --help
./install.sh native --dry-run
./install.sh native --no-packages
./install.sh vmware
```

| Option | Actual behaviour |
| --- | --- |
| `native` | Default; no forced software graphics renderer or fixed monitor name |
| `vmware` | Common desktop plus the separate VM graphics/cursor adaptations and guest dependencies |
| `--dry-run` | Preview intended files without changing configuration, backups, packages or the account shell; not a runtime dependency test |
| `--no-packages` | Skip APT and runtime builds; require working dependencies and offline-verifiable shell assets already installed or cached |
| `--waybar-only` | Deploy Waybar config/style/helper and its logo font only; no package installation or shell/SDDM changes |
| `--dolphin-only` | Deploy Dolphin-specific paint and theme selection; install missing scoped dependencies unless `--no-packages` is given |

`--no-packages` is an update/offline mode, not a fresh-machine bootstrap. Run a
normal full installation first if Rofi/Waybar compatibility builds, Zsh plugins
or the pinned prompt assets are missing.

The scoped modes are mutually exclusive. Dolphin additionally supports
`--restore-dolphin-interface` and `--interface-backup=ID` for one specific legacy
layout recovery; do not add them to an ordinary installation. See
[Dolphin recovery](dolphin-kvantum.md#interface-restoration).

## Files and backups

User targets follow `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and `XDG_STATE_HOME`, with
the usual HOME defaults. These roots must stay inside the invoking HOME;
spaces are supported, symlinked parent directories are refused. Managed root
dotfiles include `.zshrc` and `.p10k.zsh`.

User backups are under `${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe/backups/`.
They record individual files, hashes, original modes/symlinks and account-shell
state. Unrelated files are not recursively replaced. Existing MIME/KDE/Qt
settings are merged where the deployment implements a key-level merge.

System files include:

- `/etc/apt/sources.list.d/hyprixe-backports.sources`, only if backports was absent;
- `/usr/share/sddm/themes/hyprixe-frosted/`, including a greeter-readable wallpaper;
- `/etc/sddm.conf.d/zz-hyprixe-theme.conf`, selecting the theme and empty `InputMethod`;
- private SDDM backups under `/var/lib/hyprixe/sddm/backups/`.

Conflicting managed SDDM keys in higher-priority local snippets or
`/etc/sddm.conf` are neutralized with backups. Other themes, session files and
unrelated SDDM settings are retained. Read [SDDM](sddm.md) for details.

## Activate the installation

The installer does not restart SDDM or log you out. Save your work and reboot
after the first full installation so the greeter and account environment are
fresh. In SDDM select **Hyprland (uwsm-managed)**, then log in and follow
[first login](first-start.md).

`hyprctl reload` alone cannot activate a new login shell, replace the inherited
systemd environment or reload the SDDM greeter. On later updates, use the
[update guide](update.md) to select the appropriate restart.
