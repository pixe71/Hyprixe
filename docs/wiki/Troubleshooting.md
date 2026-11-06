# Troubleshooting

Start inside Hyprixe, from the checkout, as the desktop user:

```bash
./verify.sh --dependencies --session
```

Read the first relevant failure. Save work before logout/reboot; never restart
SDDM underneath an unsaved session.

## Session or missing Waybar

```bash
uwsm check is-active -v compositor-only
systemctl --user is-active graphical-session.target hyprixe-session.target
systemctl --user status waybar.service --no-pager
journalctl --user -b -u waybar.service --no-pager
```

If the graphical target is inactive, reconnect through **Hyprland (uwsm-managed)**.
Do not manually start the graphical target, remove service dependencies or spawn
a second bar. For a bar-specific problem, run `./verify.sh --waybar --session`.

## Configuration and shortcuts

```bash
hyprctl version
hyprctl configerrors
hyprctl -j binds
```

Empty/whitespace config-error output means no errors. Deploy intended changes,
reload Hyprland, and check again. Workspace shortcuts use physical number-row
positions on AZERTY. See [Keybindings](Keybindings) and [version policy](Architecture#compatibility).

## Dynamic Theming

```bash
hyprixe-theme status
hyprixe-theme refresh
hyprixe-theme status
```

| Problem | Recovery |
| --- | --- |
| Cache missing/invalid/stale | `refresh` rebuilds it from persistent state |
| Image missing | Restore the source file or `apply` a valid image |
| Wallust missing/incompatible | Run a normal `./install.sh native` |
| Uniform/pale image uses default colours | Extraction can lack enough colours; fallback is intentional |
| SDDM shows older colours/image | Retry `refresh`, then inspect the next greeter launch |
| Persistent JSON corrupt | Preserve the file/error for diagnosis; do not erase preferences blindly |

`refresh` preserves both the image selection and enabled preference. Use
`enable` only to request dynamic colours. Invalid requested images keep the old
theme; extraction failure uses Frosted Glass colours. See [Dynamic Theming](Dynamic-Theming).

## Wallpaper or login transition

```bash
systemctl --user status hyprixe-awww.service hyprixe-wallpaper.service --no-pager
journalctl --user -b -u hyprixe-awww.service -u hyprixe-wallpaper.service --no-pager
./verify.sh --session --diagnostics
sudo journalctl -b -u sddm --no-pager
```

Check state, snapshot and actual service timing before changing QML or adding
delays. Do not repeatedly kill awww. If needed, restart only
`hyprixe-wallpaper.service`. Review diagnostics before sharing personal details.

## Terminal, menus and Dolphin

| Symptom | Check |
| --- | --- |
| Kitty still opens Bash | Compare `getent passwd "$(id -un)"`, `$SHELL` and `ps -p $$ -o comm=`; reconnect after an account-shell change |
| Prompt/glyph errors | Check `zsh --version`, quiet startup, `fc-match 'Symbols Nerd Font Mono'` and installed assets |
| Rofi sidebar or clipboard fails | Check `command -v rofi`, its Wayland capabilities, and `hyprixe-clipboard.service` logs |
| Wlogout service absent | The transient `hyprixe-wlogout.service` exists only while its menu runs |
| Dolphin paint/blur wrong | Run `./verify.sh --dolphin --session`; close it before redeployment and reconnect after Qt environment changes |

Use a normal install to prepare missing compatible binaries/plugins; offline
`--no-packages` cannot create dependencies. Do not convert Bash scripts to Zsh
or change Dolphin's layout to fix paint. See [Desktop](Desktop).

## SDDM or restore failures

Run `./verify.sh --sddm`. Effective theme must be `hyprixe-frosted`, theme directory
`/usr/share/sddm/themes`, and `[General] InputMethod=` empty. Higher-priority
local configuration can override snippets; the installer backs up managed keys.
If login is unusable, use a TTY and the [SDDM-only restore](Maintenance#restore).

A restore refusing changed files is protecting later edits. Preserve your changes,
inspect the backup and use the documented recovery options. Package conflicts
require matching Debian stable/backports runtime and development packages;
do not bypass them with a global backports pin or disabled validation.
