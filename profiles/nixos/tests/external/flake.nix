{
  description = "Independent host fixture for the public Hyprixe modules";

  inputs = {
    hyprixe.url = "github:pixe71/Hyprixe";
    nixpkgs.follows = "hyprixe/nixpkgs";
    home-manager.follows = "hyprixe/home-manager";
  };

  outputs = { hyprixe, nixpkgs, home-manager, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      inherit (pkgs) lib;
      hostModule =
        {
          desktop ? true,
          homeDesktop ? desktop,
          secondDesktop ? false,
          container ? true,
          sddm ? false,
          theme ? sddm,
          synchronization ? false,
          publishers ? [ "pilot" "observer" ],
          homeOverrides ? { },
        }:
        {
          imports = [
            ./configuration.nix
            hyprixe.nixosModules.default
            home-manager.nixosModules.home-manager
          ];
          services.xserver.enable = lib.mkDefault sddm;
          services.displayManager.sddm.enable = lib.mkDefault sddm;
          programs.hyprixe = {
            enable = lib.mkDefault desktop;
            sddm.enable = lib.mkDefault theme;
            sddm.sync = {
              enable = lib.mkDefault synchronization;
              users = lib.mkDefault publishers;
            };
          };
          home-manager.users = {
            pilot = {
              imports = [ hyprixe.homeManagerModules.default homeOverrides ];
              programs.hyprixe.enable = lib.mkDefault homeDesktop;
            };
            observer = {
              imports = [ hyprixe.homeManagerModules.default ];
              programs.hyprixe.enable = lib.mkDefault secondDesktop;
            };
          };
        } // lib.optionalAttrs container {
          boot.isContainer = true;
          nixpkgs.hostPlatform = system;
        };

      makeHost = args: nixpkgs.lib.nixosSystem { modules = [ (hostModule args) ]; };
      hosts = {
        disabled = makeHost { desktop = false; };
        desktop = makeHost {
          homeOverrides.programs.rofi.enable = true;
        };
        two = makeHost { secondDesktop = true; };
        static = makeHost { sddm = true; };
        dynamic = makeHost { sddm = true; synchronization = true; secondDesktop = true; };
      };
      homeFor = host: host.config.home-manager.users.pilot;
      observerFor = host: host.config.home-manager.users.observer;
      unitsFor = host: host.config.systemd;
    in
    {
      nixosConfigurations = hosts;
      packages.${system}.session-vm = pkgs.testers.runNixOSTest (import (hyprixe.outPath + "/profiles/nixos/tests/session-vm.nix") {
        inherit pkgs;
        host = hostModule { desktop = false; container = false; };
        username = "pilot";
        homeDirectory = "/home/pilot-d1";
        configDirectory = "settings";
        peer = "observer";
        inherit (hyprixe.packages.${system}) rofi;
        gtkPython = import (hyprixe.outPath + "/profiles/nixos/packages/gtk-python.nix") { inherit pkgs; };
      });

      lib.invalid = {
        noCompositor = makeHost { desktop = false; homeDesktop = true; };
        missingSddm = makeHost { theme = true; };
        missingTheme = makeHost { sddm = true; theme = false; synchronization = true; };
        emptyPolicy = makeHost { sddm = true; synchronization = true; publishers = [ ]; };
        unknownPublisher = makeHost { sddm = true; synchronization = true; publishers = [ "ghost" ]; };
        reservedPublisher = (makeHost {
          sddm = true;
          synchronization = true;
          publishers = [ "hyprixe-theme" ];
        }).extendModules { modules = [ { users.users.hyprixe-theme.isNormalUser = true; } ]; };
        duplicateWaybar = makeHost { homeOverrides.programs.waybar.enable = true; };
        duplicateKitty = makeHost { homeOverrides.programs.kitty.enable = true; };
        duplicateZsh = makeHost { homeOverrides.programs.zsh.enable = true; };
        duplicateHyprland = makeHost { homeOverrides.wayland.windowManager.hyprland.enable = true; };
      };

      checks.${system}.public-modules =
        assert (homeFor hosts.desktop).home.homeDirectory == "/home/pilot-d1";
        assert (homeFor hosts.desktop).home.stateVersion == "25.11";
        assert hosts.desktop.config.system.stateVersion == "25.11";
        assert hosts.desktop.config.networking.hostName == "aster";
        assert !hosts.desktop.config.services.displayManager.sddm.enable;
        assert hosts.desktop.config.programs.hyprland.withUWSM;
        assert !((observerFor hosts.desktop).xdg.configFile ? "hypr/hyprland.lua");
        assert (observerFor hosts.two).xdg.configFile ? "hypr/hyprland.lua";
        assert (observerFor hosts.two).xdg.stateHome != (homeFor hosts.two).xdg.stateHome;
        assert !((unitsFor hosts.two).sockets ? hyprixe-sddm-sync);
        assert !((unitsFor hosts.static).sockets ? hyprixe-sddm-sync);
        assert (unitsFor hosts.dynamic).sockets ? hyprixe-sddm-sync;
        assert builtins.elem "hyprixe-sddm-sync" hosts.dynamic.config.users.users.observer.extraGroups;
        assert !((homeFor hosts.disabled).xdg.configFile ? "hypr/hyprland.lua");
        pkgs.runCommand "hyprixe-external-host" { } ''
          for activation in ${lib.concatMapStringsSep " " (host: (homeFor host).home.activationPackage) [ hosts.desktop hosts.static hosts.two hosts.dynamic ]}; do
            test -f "$activation/home-files/settings/hypr/hyprland.lua"
            test -f "$activation/home-files/settings/systemd/user/hyprixe-session.target"
            test -x "$activation/home-path/bin/hyprixe-theme"
            test -x "$activation/home-path/bin/awww"
            grep -Fqx 'Owned by the host' "$activation/home-files/.existing-home-file"
          done
          test -e ${(homeFor hosts.desktop).home.activationPackage}/home-files/settings/rofi/config.rasi
          test ! -e ${(observerFor hosts.desktop).home.activationPackage}/home-files/.config/hypr/hyprland.lua
          test -e ${(observerFor hosts.two).home.activationPackage}/home-files/.config/hypr/hyprland.lua
          grep -Fq 'HYPRIXE_LOGIN_THEME_SYNC=0' ${(observerFor hosts.two).home.activationPackage}/home-path/bin/hyprixe-theme
          grep -Fq 'HYPRIXE_LOGIN_THEME_SYNC=1' ${(observerFor hosts.dynamic).home.activationPackage}/home-path/bin/hyprixe-theme
          test ! -e ${(homeFor hosts.disabled).home.activationPackage}/home-files/settings/hypr/hyprland.lua
          grep -Fq 'HYPRIXE_LOGIN_THEME_SYNC=1' \
            ${(homeFor hosts.dynamic).home.activationPackage}/home-path/bin/hyprixe-theme
          touch "$out"
        '';
    };
}
