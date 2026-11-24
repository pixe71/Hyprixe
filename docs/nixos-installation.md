# Install Hyprixe on NixOS

Hyprixe brings its Frosted Glass desktop to an existing NixOS installation.
The tested configuration uses NixOS **26.05**, Home Manager **release-26.05**
and **`x86_64-linux`**. The working profile is still **planned**. For a trial,
use a complete local copy of Hyprixe that includes `flake.nix`, `flake.lock`,
`profiles/nixos/` and `common/`. Other releases and architectures need their
own package, build and graphical-session validation.

The default wallpaper's redistribution terms are still unresolved. Follow
the [asset release checklist](wiki/Assets.md#evidence-and-release-checklist)
before distributing a candidate.

Use an existing local account and a working NixOS generation. Keep access to
a text console and the earlier generation. If Flake commands are unavailable,
enable them through your host's normal configuration workflow with
`nix.settings.experimental-features = [ "nix-command" "flakes" ];`, keeping
any other features your configuration already needs.
Keep the host's hardware modules, boot settings, account, shell and
`system.stateVersion`. Preserve any existing `home.stateVersion`.

## With an existing Flake

Add this input in the host's `flake.nix`, replacing the example with the
absolute Linux path of the complete source. An explicit `path:` includes
files that Git-based Flake references can exclude.

```nix
inputs.hyprixe.url = "path:/absolute/path/to/Hyprixe";
```

After a revision containing the profile is published, you can use
`inputs.hyprixe.url = "github:pixe71/Hyprixe";`. The current public `main`
does not contain the complete candidate. To reproduce the tested dependency
pair, the examples below use the inputs from Hyprixe's lock.

Open the host's existing `nixpkgs.lib.nixosSystem` definition. Add `hyprixe`
to its `outputs` arguments if necessary. Add these module entries to its
existing `modules` list. Replace `alex` with a real account already declared
by the host. Retain any existing Home Manager imports for the account.

```nix
hyprixe.nixosModules.default
{
  programs.hyprixe.enable = true;

  home-manager.users.alex = {
    imports = [ hyprixe.homeManagerModules.default ];
    programs.hyprixe.enable = true;
  };
}
```

If the host lacks integrated Home Manager, add its `release-26.05` input,
import its NixOS module once in the same list, and specify
`home.stateVersion = "26.05";` for the new Home Manager configuration.
With existing Home Manager, keep its import and state version. Use a single
Nixpkgs and Home Manager release pair. The tested pairing is reproduced by
making the host inputs follow `hyprixe/nixpkgs` and `hyprixe/home-manager`,
as shown below. Replace existing input URL definitions if you switch to
`follows`, and review the effect on the rest of your host first. A host that
keeps its own pins should use the compatible 26.05 releases and validate its
build before activation. [Home Manager Flake integration](https://nix-community.github.io/home-manager/nix-flakes.html)

## With a traditional `configuration.nix`

Add a small `flake.nix` next to your existing `configuration.nix`. This wraps
your existing modules with pinned inputs. It works with the host's existing
`hardware-configuration.nix` import and does not rebuild the directory
layout. The first build uses the Flake's pinned Nixpkgs rather than the
system channel. Review that change before activating. Keep the original
configuration and a bootable generation available as a recovery path.

In this complete example, change the source path and account. `desktop` is
the key used to select the NixOS configuration. Keep the host's platform
definition in its existing modules. Use your existing Home Manager state
version if the account already has one.

```nix
{
  inputs = {
    hyprixe.url = "path:/absolute/path/to/Hyprixe";
    nixpkgs.follows = "hyprixe/nixpkgs";
    home-manager.follows = "hyprixe/home-manager";
  };

  outputs = { nixpkgs, home-manager, hyprixe, ... }: {
    nixosConfigurations.desktop = nixpkgs.lib.nixosSystem {
      modules = [
        ./configuration.nix
        home-manager.nixosModules.home-manager
        hyprixe.nixosModules.default
        {
          home-manager.useGlobalPkgs = true;
          programs.hyprixe.enable = true;
          home-manager.users.alex = {
            imports = [ hyprixe.homeManagerModules.default ];
            home.stateVersion = "26.05";
            programs.hyprixe.enable = true;
          };
        }
      ];
    };
  };
}
```

Move any channel-based Home Manager `<home-manager/nixos>` import out of the
trial configuration so only the pinned module is imported. Other legacy
`<...>` channel imports and absolute paths outside the Flake tree must be
adapted to explicit inputs or paths available during pure evaluation. Leave
hardware and boot declarations with the host. This procedure uses Flakes
for evaluation and rebuild. The validation fixture starts from a plain
[`configuration.nix`](../profiles/nixos/tests/external/configuration.nix)
and adds the public modules in an external wrapper. [NixOS rebuild locations](https://wiki.nixos.org/wiki/Nixos-rebuild)

## Choose the login method

Enabling the Hyprixe desktop supplies Hyprland and UWSM. The host selects the
login method. In a display manager that offers the Wayland session, choose
**Hyprland (uwsm-managed)**. From a local text-console login, UWSM can start
the same compositor with `uwsm start -e -D Hyprland hyprland.desktop`.
Use this command as the account that will run the desktop.
[UWSM launch reference](https://github.com/Vladimir-csp/uwsm#usage)

SDDM with the **X11 greeter and Wayland desktop session** is the graphical
login tested in the VM. The no-SDDM configuration is evaluated and built.
Console login, other display managers and the SDDM Wayland greeter have not
had a dedicated graphical validation in this profile.

If you choose the tested SDDM setup, add this system module entry. Merge it
with the host's existing display-manager configuration.

```nix
{
  services.xserver.enable = true;
  services.displayManager.sddm.enable = true;
  services.displayManager.defaultSession = "hyprland-uwsm";
  programs.hyprixe.sddm.enable = true;
  programs.hyprixe.sddm.sync.enable = false;
}
```

The greeter uses the packaged wallpaper and palette. See the
[profile reference](../profiles/nixos/README.md#publishing-the-shared-greeter-snapshot)
for optional publication and its trust boundary.

## Build, activate and log in

Review existing files in your home directory before activating. Home Manager
reports collisions with files already owned by you or another configuration.
Read the error, save your originals and decide which module should own each
file before retrying. The [profile reference](../profiles/nixos/README.md#session-and-existing-files)
lists competing program definitions. Hyprixe can be enabled for one or more
already-declared accounts. Add the user module and its enable option to each
chosen account.

From the host Flake directory, set `target` to the key of your host under
`nixosConfigurations`. These commands lock and build without activation.
Use a Flake directory that contains the configuration sources only.

```sh
target=desktop
nix flake lock "path:$PWD"
nix build --no-link "path:$PWD#nixosConfigurations.$target.config.system.build.toplevel"
```

Save your work and use a verified text console for the first activation.
`test` changes the running system and can affect the display manager. It
leaves the boot default in place.

```sh
sudo nixos-rebuild test --flake "path:$PWD#$target"
```

Log in to the UWSM session. Try **Super+Return** for Kitty, **Super+Space**
for Rofi and `hyprixe-theme status` for the wallpaper and palette. Use
`hyprixe-theme apply /path/to/image.jpg` to select a wallpaper. Review the
[profile's settings](../profiles/nixos/README.md#personal-settings) and
[theme commands](../profiles/nixos/README.md#dynamic-wallpaper-theming).

To change the default desktop keyboard layout, copy the Core's
[`user_settings.lua`](../common/config/hypr/UserConfigs/user_settings.lua)
into your own configuration and change `kb_layout`. Add this entry in a
Home Manager module for that account.

```nix
{ lib, ... }:
{
  xdg.configFile."hypr/UserConfigs/user_settings.lua".source = lib.mkForce ./user_settings.lua;
}
```

Configure the greeter keyboard using your host settings.

After confirming login and recovery, `sudo nixos-rebuild switch --flake
"path:$PWD#$target"` activates the configuration and makes it the boot
default using the host's existing boot configuration. [NixOS manual on configuration changes](https://nixos.org/manual/nixos/stable/#sec-changing-config)

## Update, roll back and uninstall

- Save the host sources and lock together. For a published GitHub input, run
  `nix flake update hyprixe --flake "path:$PWD"` from the host directory.
  Review changes to followed inputs. For a local candidate, update the source
  path and refresh its lock. Build and test before adopting it.
- If a temporary test fails, select the previously recorded working boot
  generation when you reboot. If you already made a new generation persistent,
  `sudo nixos-rebuild switch --rollback` can restore the previous generation.
  Keep a verified console or recovery environment available. Restore the
  matching host sources and lock before your next build. Personal files and
  writable theme state are separate from the system rollback.
- To remove Hyprixe, disable it for each Home Manager account and at system
  scope. Disable `programs.hyprixe.sddm.sync.enable` and
  `programs.hyprixe.sddm.enable` if used, and restore any host session override
  added only for the trial. Make sure the host has a usable session or text
  login. Build and activate this configuration, then start a fresh login.
  Hyprixe's declarative files and units are removed from the active
  generation. User themes, preferences and snapshots remain. You can remove
  the module imports and input in a subsequent configuration change.

## Troubleshooting

- **Evaluation fails**. Check the host and Home Manager error messages for
  duplicate modules and SDDM options. Run `nix flake show "path:$PWD"` to
  confirm the selected host key and that local source files are included.
- **Home Manager reports an existing file**. Read `journalctl -b -u
  home-manager-ACCOUNT.service` with the actual account name. Preserve the
  file and resolve ownership before retrying.
- **Login fails**. From a text console, check `journalctl -b -u
  display-manager.service` if using SDDM. Select the UWSM entry. In a running
  session, run `hyprctl configerrors -j` and `systemctl --user --failed`.
- **Wallpaper or colours do not update**. Check `hyprixe-theme status` and
  `journalctl --user -b -u hyprixe-wallpaper.service -u waybar.service`.
  Repair the selected image or cache. If panels started with fallback CSS,
  restart `waybar.service` and `swaync.service` in the user manager.
