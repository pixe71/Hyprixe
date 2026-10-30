# First login

[Documentation index](README.md)

After the first installation, save your work and reboot. In SDDM's session
chooser select **Hyprland (uwsm-managed)**. The plain Hyprland entry does not
provide the session lifecycle required by Hyprixe's services.

UWSM starts the compositor, publishes its environment to systemd and owns
`graphical-session.target`. Hyprixe finalizes that environment from Hyprland and
starts its service target. Merely setting `WAYLAND_DISPLAY` does not activate
a graphical session. Do not manually start `graphical-session.target` to work
around a wrong session selection.

## Initial checks

Open Kitty with `SUPER + Return`, then run from your checkout:

```bash
hyprctl version
hyprctl configerrors
uwsm check is-active -v compositor-only
systemctl --user is-active graphical-session.target hyprixe-session.target
systemctl --user status waybar.service hyprixe-awww.service hyprixe-wallpaper.service --no-pager
./verify.sh --dependencies --session
```

The config-error output should be empty, targets active, Waybar/awww running
and the wallpaper oneshot service `active (exited)`. A successful verifier ends
with `RESULT: 0 failed check(s)`. Read any `FAIL` rather than assuming every
`SKIPPED` is an error; see [verification](verification.md).

Check the account shell in the newly opened terminal:

```bash
zsh --version
echo "$SHELL"
ps -p $$ -o comm=
```

The shell should be Zsh with the supplied Powerlevel10k prompt. A terminal
opened before the account-shell change can remain Bash until the entire
desktop session is reconnected.

## Check the desktop interactively

- Confirm the forest wallpaper, four persistent Waybar workspaces and the taskbar.
- Type directly in `SUPER + Space`; test clipboard with `SUPER + CTRL + V`
  and windows with `ALT + F10`.
- Test `ALT + Tab` and its reverse with several windows on the current workspace.
- Open Dolphin and confirm readable light glass without unwanted layout changes.
- Open the four-action Wlogout menu with either session shortcut; dismiss it
  with Escape. Logout, shutdown and reboot ask for confirmation.
- Test `SUPER + L` and unlock with your account password before relying on locking.
- Test screenshots, audio, network and any brightness/battery hardware available.

The default keyboard is French AZERTY (`fr`, `latin9`). Workspace shortcuts use
physical number-row positions; see [keybindings](keybindings.md). Review
[customization](customization.md) if your keyboard needs another layout.

These are manual acceptance checks. The verifier does not press keys, unlock
PAM, judge GPU blur or certify the SDDM-to-desktop transition visually.
