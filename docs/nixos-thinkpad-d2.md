# Hyprixe on a ThinkPad · physical validation plan

Use this guide to prepare D2a. The activation steps require separate approval
for D2b. Start the trial from an existing, working NixOS
26.05 installation with a non-graphical login available. The
[external flake example](../profiles/nixos/README.md#install-from-an-external-flake)
adds the Hyprixe modules to that installation. Keep your host-specific
hardware configuration, AZERTY layout, GRUB, EFI settings, Windows Boot
Manager, disks, partitions and filesystem UUIDs under host control.

## Read-only preflight on the target

Run these checks from Linux on the ThinkPad. Record the model, distribution,
actual host configuration key, target account and booted system closure.
The host configuration key comes from the host Flake's `nixosConfigurations`
output. It often matches `hostnamectl --static`.

```sh
cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name
cat /etc/os-release
uname -r
systemd-detect-virt
hostnamectl --static
command -v nix nixos-rebuild
ls -ld /run/booted-system /run/current-system
readlink -f /run/booted-system
readlink -f /run/current-system
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
```

For D2a, the accessible host was a Windows MSI PC, with the Debian 13 test
shell running in WSL2. The accessible `Config-NixOS` checkout contained
only a README. There was no host or account configuration to evaluate.
If the ThinkPad has no native NixOS installation, prepare its base system
as a separate task. That task needs verified backups and Windows recovery
access, a confirmed UEFI and disk layout, and a working base NixOS generation
with a normal local account and console access. Hyprixe can be tested after
that base system and the existing Windows boot path have both been verified.

## Establish a recovery point

1. Record the working NixOS generation and verify that GRUB can start it.
   Verify that the existing Windows entry still starts Windows. Keep the
   current NixOS generation available throughout the trial.
2. Save the external Flake, its lock file and host configuration together.
   Review the diff for changes to boot, storage, networking, user accounts,
   keyboard layout and state versions. This trial needs only the desktop,
   Home Manager and optional greeter configuration.
3. Check that you can log in from a virtual console and locate the original
   configuration there. Try `Ctrl+Alt+F3` and authenticate before starting
   the trial. Verify that the recorded system closure is readable and that
   you can get administrative access from this console. Review Home Manager
   link collisions and preserve your personal files, including `.zshrc`,
   any existing Hyprland and application configuration, and the XDG theme
   state. Keep the known-good system generation and its store paths available
   throughout the trial.
4. From the host Flake directory, substitute the existing configuration name
   for `your-host`. Build the configuration before attempting a live test.

   ```sh
   nix eval --raw '.#nixosConfigurations.your-host.config.system.build.toplevel.drvPath'
   nix build --no-link '.#nixosConfigurations.your-host.config.system.build.toplevel'
   ```

## First-trial inputs and configuration

Use the [Flake integration guide](../profiles/nixos/README.md#install-from-an-external-flake)
for the public module imports. Unpack a verified, complete local candidate
on a Linux filesystem on the target, check that `flake.nix`, `flake.lock`,
`common/` and `profiles/nixos/` are present, and use its actual `realpath`
for an explicit `path:` input. A trial Flake using `path:./hyprixe-source`
instead expects the candidate inside that directory. Reference that trial
Flake with `path:` too while its source files are untracked.

Keep the host's existing modules and local account. Use one Home Manager
integration and one owner for each desktop service and dotfile. Keep both
state versions from the original host configuration. Compare stable
Nixpkgs and Home Manager revisions before changing which inputs the host
follows.

Set NixOS `programs.hyprixe.enable = true`, the selected Home Manager user's
`programs.hyprixe.enable = true`, `programs.hyprixe.sddm.enable = true` and
`programs.hyprixe.sddm.sync.enable = false`. Select the native SDDM service
and `hyprland-uwsm`. The reference setup uses X11 for the greeter and
Wayland for the session. It expects the greeter's keyboard layout from the
host. The Core desktop uses French AZERTY by default.

## First activation on the ThinkPad

Run this step from a text login during the approved D2 trial, with work
saved and the previous boot generation available. End the graphical session
before running the test. Use the statically configured Frosted Glass greeter
and leave publication disabled for the first session.

```sh
sudo nixos-rebuild test --flake '.#your-host'
```

`test` changes the running system, including applicable services and Home
Manager activation. It leaves the current boot default in place. The first
trial ends with an explicit check that the known-good system is recoverable.
Schedule any persistent activation separately once the hardware checks pass.
[NixOS manual on configuration changes](https://nixos.org/manual/nixos/stable/#sec-changing-config)

## Recovery during an approved trial

1. If SDDM fails, use the verified text console. Read `systemctl status
   display-manager.service` and `journalctl -b -u display-manager.service`.
   If SDDM works and Hyprland fails, check the `hyprland-uwsm` selection and
   `journalctl --user -b`. Run `hyprctl configerrors -j` only if a Hyprland
   instance responds.
2. To recover in the current boot, use the recorded known-good store path.
   Replace `KNOWN_GOOD_SYSTEM` with that saved path and verify that
   `bin/switch-to-configuration` exists there before running
   `sudo "$KNOWN_GOOD_SYSTEM/bin/switch-to-configuration" test` from the
   console. This is a live activation of the known-good closure.
3. If the console is unavailable, boot the verified NixOS generation from
   the existing GRUB menu. Rebooting restores the selected boot generation.
   It does not undo changes to writable files. If the known-good generation
   cannot start, use the previously verified recovery environment and stop
   the trial.
4. Restore the saved host sources and lock, or remove the Hyprixe imports
   and option declarations in a separate, reviewed change. Build the
   original configuration before another activation. Preserve personal
   files and the writable Hyprixe state. Recover individual user files from
   their pretrial copies only if needed.

## Record the physical results

| Check | How to verify | Expected result |
| --- | --- | --- |
| Dual boot | Record the existing GRUB entries. Select the known-good NixOS entry and the existing Windows entry once each. | Both boot. The menu entries are still present after the temporary trial. |
| Static greeter | Check the panel, bundled wallpaper, user and **Hyprland (uwsm-managed)** option. Run `test ! -S /run/hyprixe-sddm-sync.sock` from a console. | Login works and the static theme needs no publication socket. |
| UWSM and Hyprland | Check `uwsm check is-active compositor-only`, `hyprctl configerrors -j` and `systemctl --user --failed` in the session. | The compositor is managed by UWSM, with no Hyprland config errors or failed Hyprixe units. |
| Desktop apps | Click Waybar workspaces and taskbar. Use Super+Space, Super+Return and Super+E. Launch an application from Rofi and open a local folder in Dolphin. | Workspaces and focus change, Kitty opens with Zsh, and Dolphin opens with the Frosted Glass Qt style. |
| Keyboard and touchpad | Check the greeter's keyboard selection and type test characters in Kitty. Try movement, tap, scroll and configured gestures. | AZERTY works at login and in the session. Touchpad input is usable. |
| Panel and external screen | Inspect the panel, connect and disconnect an external screen, and compare `hyprctl monitors` before and after. | External display is detected and removed. Layout, wallpaper, Waybar and DPMS recover. |
| Wi-Fi and firewall | Connect or reconnect to a known network, check local connectivity, and inspect `systemctl status firewall.service` when using the native NixOS firewall. | Connectivity works and the configured host firewall is active. |
| Bluetooth and audio | Pair a known device and test playback, output selection and a microphone. If the host uses WirePlumber, check `wpctl status`. | Relevant devices remain usable after reconnect and resume. |
| Battery and power | Unplug and reconnect AC. Compare battery reporting and the active profile in the host's configured power manager. | Battery and AC states update and the intended balanced profile is available. |
| Backlight and popup | Use the brightness keys, Waybar scroll and GTK slider. Check the 5% floor, immediate screen changes, Escape, second click and the three-second timeout off the popup. | The real panel responds and the popup closes as designed. |
| Lock, DPMS and suspend | Lock with Super+L and try one incorrect credential. Check configured idle/DPMS timeouts, then suspend and resume from the lid or session. | The desktop stays inaccessible until PAM accepts the login. Display, Wi-Fi and audio recover. |
| Notifications and Polkit | Send `notify-send 'Hyprixe D2' 'Notification test'`, open SwayNC and trigger the host's approved graphical authentication prompt. | Notification and centre are visible. One Polkit prompt appears and can be cancelled. |
| Clipboard and session menu | Copy text and an image and restore each via Super+Ctrl+V. Open Wlogout, cancel a confirmation and then test a normal logout. | Both clipboard types restore. UWSM and its services stop and SDDM returns. |
| Theme and persistence | Check `hyprixe-theme status`, apply a valid personal image, try a disposable invalid image, then log out and in. Try `hyprixe-theme default` afterwards. | Wallust produces a palette, changes reach the consumers, the bad image leaves the last valid theme intact, and the saved selection survives login. The default restores the bundled wallpaper. |
| Rollback and removal | Recover the recorded generation from the console or GRUB. Check user files and the base desktop or console. | Login returns and personal settings are preserved when the trial configuration is withdrawn. |
| Optional SDDM publication | In a separately approved follow-up, enroll the target local account, publish a theme, log out and reboot. Check a regular unenrolled account when one is available. | The last authorized valid snapshot is displayed and retained. Unenrolled access cannot publish. |

Record the generation, whether SDDM sync was enabled and any failing step.
Useful diagnostics include `hyprctl configerrors -j`, `hyprixe-theme status`,
`systemctl --user --failed` and the [profile's session and greeter logs](../profiles/nixos/README.md).
If palette restoration fails, inspect `journalctl --user -b -u
hyprixe-wallpaper.service -u waybar.service -u swaync.service`. Check the
selected image and XDG state before using `hyprixe-theme refresh` in the
session. If either panel started with fallback CSS and stays on it after
recovery, restart it with `systemctl --user restart waybar.service
swaync.service`. Keep the optional Konsole panel out of the trial.

The D1 dynamic greeter logged a missing optional `Palette.qml` on an empty
state and displayed the fallback. D2a did not retest that warning on hardware.
Dynamic publication is opt-in because the greeter loads QML generated by
the isolated receiver. A future design can give static, trusted QML a
strict reader of inert palette data and a validated image snapshot.
Leave the experimental generation inactive if login, lock, suspend or the
normal boot choices fail.
