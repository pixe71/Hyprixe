{
  nixpkgs,
  home-manager,
  hyprixe,
  system,
}:

let
  inherit (nixpkgs) lib;
  pkgs = nixpkgs.legacyPackages.${system};

  username = "hyprixe-fixture";
  homeDirectory = "/home/${username}";
  configDirectory = ".config-fixture";
  monitorFile = "hypr/UserConfigs/monitors.lua";
  coreHypr = ../../../common/config/hypr;
  canonicalMonitor = coreHypr + "/UserConfigs/monitors.lua";
  target = "systemd/user/hyprixe-session.target";

  # The host owns Home Manager, account settings, and the XDG layout.
  hostModule =
    {
      importHyprixe,
      enable ? false,
      customXdg ? true,
      sddm ? false,
      sync ? false,
    }:
    {
      imports = [ home-manager.nixosModules.home-manager ]
        ++ lib.optional importHyprixe hyprixe.nixosModules.default;
      system.stateVersion = "26.05";
      users.users.${username} = {
        isNormalUser = true;
        home = homeDirectory;
      };

      home-manager.useGlobalPkgs = true;
      home-manager.users.${username} = {
        imports = lib.optional importHyprixe hyprixe.homeManagerModules.default;
        home.stateVersion = "26.05";
        xdg.enable = true;
      }
      // lib.optionalAttrs customXdg {
        xdg.configHome = "${homeDirectory}/${configDirectory}";
        xdg.dataHome = "${homeDirectory}/.data-fixture";
        xdg.cacheHome = "${homeDirectory}/.cache-fixture";
        xdg.stateHome = "${homeDirectory}/.state-fixture";
      }
      // lib.optionalAttrs enable {
        programs.hyprixe.enable = true;
      };
    }
    // lib.optionalAttrs enable { programs.hyprixe.enable = true; }
    // lib.optionalAttrs sddm {
      services.displayManager.sddm.enable = true;
      services.xserver.enable = true;
      programs.hyprixe.sddm = {
        enable = true;
        sync = { enable = sync; users = [ username ]; };
      };
    };

  host =
    args:
    (lib.nixosSystem {
      modules = [
        { nixpkgs.hostPlatform = system; }
        (hostModule args)
      ];
    }).config;

  baseline = host { importHyprixe = false; };
  disabled = host { importHyprixe = true; };
  enabled = host {
    importHyprixe = true;
    enable = true;
  };
  enabledDefault = host {
    importHyprixe = true;
    enable = true;
    customXdg = false;
  };
  staticGreeter = host { importHyprixe = true; sddm = true; };
  dynamicGreeter = host { importHyprixe = true; sddm = true; sync = true; };
  sddm = import ../packages/sddm.nix { inherit pkgs; };
  dynamicSddm = import ../packages/sddm.nix { inherit pkgs; dynamic = true; };
  unit = "hyprixe-sddm-sync";
  noReceiver = cfg: !(builtins.hasAttr unit cfg.systemd.sockets) && !(builtins.hasAttr unit cfg.systemd.services)
    && !(cfg.users.users ? hyprixe-theme) && !(cfg.environment.etc ? "hyprixe/sddm-sync-users.json");
  greeterCheck =
    assert noReceiver disabled && noReceiver enabled && noReceiver staticGreeter;
    assert staticGreeter.services.displayManager.sddm.theme == sddm.name;
    assert dynamicGreeter.services.displayManager.sddm.theme == sddm.name;
    assert staticGreeter.services.displayManager.sddm.settings.Theme.EnableAvatars == false;
    assert lib.elem pkgs.kdePackages.qtdeclarative staticGreeter.services.displayManager.sddm.extraPackages;
    assert lib.elem pkgs.kdePackages.qtsvg staticGreeter.services.displayManager.sddm.extraPackages;
    assert lib.elem sddm.theme staticGreeter.environment.systemPackages;
    assert lib.elem dynamicSddm.theme dynamicGreeter.environment.systemPackages;
    assert dynamicGreeter.users.users.hyprixe-theme.isSystemUser;
    assert dynamicGreeter.systemd.services.${unit}.serviceConfig.ProtectHome;
    assert dynamicGreeter.systemd.sockets.${unit}.socketConfig.SocketMode == "0660";
    assert dynamicGreeter.environment.etc."hyprixe/sddm-sync-users.json".mode == "0444";
    assert dynamicGreeter.system.stateVersion == baseline.system.stateVersion;
    assert dynamicGreeter.networking.hostName == baseline.networking.hostName;
    pkgs.runCommand "hyprixe-sddm-profiles" { } ''
      static=${sddm.theme}/share/sddm/themes/${sddm.name}
      dynamic=${dynamicSddm.theme}/share/sddm/themes/${sddm.name}
      for file in Main.qml components/DynamicTheme.qml components/GlassPane.qml assets/user.svg; do
        cmp "${../../../common/sddm/themes/hyprixe-frosted}/$file" "$static/$file"
        cmp "$static/$file" "$dynamic/$file"
      done
      cmp "${../../../common/wallpapers/min_forest.jpg}" "$static/min_forest.jpg"
      grep -Fx 'dynamicPalette=' "$static/theme.conf"
      grep -Fx 'dynamicPalette=file:///var/lib/hyprixe/theme/current/Palette.qml' "$dynamic/theme.conf"
      test -x ${lib.getExe dynamicSddm.receiver}
      test -x ${lib.getExe dynamicSddm.client}
      touch "$out"
    '';

  homeOf = config: config.home-manager.users.${username};
  disabledHome = homeOf disabled;
  enabledHome = homeOf enabled;
  hyprland = enabled.programs.hyprland.package;
  inherit (import ../packages { inherit pkgs; }) rofi wallust;
  gtkPython = import ../packages/gtk-python.nix { inherit pkgs; };
  sessionNames = lib.concatMap (package: package.providedSessions)
    enabled.services.displayManager.sessionPackages;

  runtime = config: {
    systemPackages = map (package: package.outPath) config.environment.systemPackages;
    homePackages = map (package: package.outPath) (homeOf config).home.packages;
    systemServices = builtins.attrNames config.systemd.services;
    systemUserServices = builtins.attrNames config.systemd.user.services;
    homeServices = builtins.attrNames (homeOf config).systemd.user.services;
  };
  verifyConfig = ''
    unset WAYLAND_DISPLAY DISPLAY HYPRLAND_INSTANCE_SIGNATURE DBUS_SESSION_BUS_ADDRESS
    export XDG_RUNTIME_DIR="$TMPDIR/runtime"
    export XDG_CACHE_HOME="$TMPDIR/cache"
    export XDG_DATA_HOME="$TMPDIR/data"
    export XDG_STATE_HOME="$TMPDIR/state"
    install -d -m 700 "$XDG_RUNTIME_DIR"
    ${lib.getExe hyprland} --verify-config
  '';
  profileDisabled =
    assert !disabled.programs.hyprixe.enable;
    assert !disabledHome.programs.hyprixe.enable;
    assert disabled.programs.hyprland.enable == baseline.programs.hyprland.enable;
    assert disabled.programs.hyprland.withUWSM == baseline.programs.hyprland.withUWSM;
    assert disabled.programs.uwsm.enable == baseline.programs.uwsm.enable;
    assert disabled.services.displayManager.sessionPackages == baseline.services.displayManager.sessionPackages;
    assert disabled.services.displayManager.sddm.enable == baseline.services.displayManager.sddm.enable;
    assert disabled.services.displayManager.defaultSession == baseline.services.displayManager.defaultSession;
    assert !(builtins.hasAttr monitorFile disabledHome.xdg.configFile);
    assert builtins.attrNames disabledHome.home.file == builtins.attrNames (homeOf baseline).home.file;
    assert runtime disabled == runtime baseline;
    assert (disabled.security.pam.services ? hyprlock) == (baseline.security.pam.services ? hyprlock);
    assert disabled.users.users.${username}.shell == baseline.users.users.${username}.shell;
    pkgs.runCommand "hyprixe-profile-disabled" { } ''
      files='${disabledHome.home.activationPackage}/home-files'
      for name in 'hypr/hyprland.lua' '${monitorFile}' '${target}'; do
        test ! -e "$files/${configDirectory}/$name"
        test ! -L "$files/${configDirectory}/$name"
      done
      touch "$out"
    '';

  profileEnabled =
    assert enabled.programs.hyprixe.enable;
    assert enabledHome.programs.hyprixe.enable;
    assert enabledHome.home.username == username;
    assert enabledHome.home.homeDirectory == homeDirectory;
    assert enabled.programs.hyprland.enable && enabled.programs.hyprland.withUWSM;
    assert enabled.programs.uwsm.enable && enabled.programs.uwsm.waylandCompositors == { };
    assert sessionNames == [ "hyprland" "hyprland-uwsm" ];
    assert enabled.services.displayManager.sddm.enable == baseline.services.displayManager.sddm.enable;
    assert enabled.services.displayManager.defaultSession == baseline.services.displayManager.defaultSession;
    assert enabled.security.polkit.enable && enabled.xdg.portal.enable;
    assert enabled.security.pam.services ? hyprlock;
    assert !enabled.services.hypridle.enable && !enabled.programs.hyprlock.enable;
    assert enabled.users.users.${username}.shell == baseline.users.users.${username}.shell;
    assert lib.elem enabled.programs.hyprland.portalPackage enabled.xdg.portal.extraPortals;
    assert lib.elem pkgs.xdg-desktop-portal-gtk enabled.xdg.portal.extraPortals;
    assert !enabledHome.wayland.windowManager.hyprland.enable;
    assert enabledHome.xdg.configFile.${monitorFile}.source == canonicalMonitor;
    assert (runtime enabled).homeServices == (runtime baseline).homeServices;
    assert lib.elem pkgs.kitty enabledHome.home.packages;
    assert lib.elem pkgs.awww enabledHome.home.packages;
    pkgs.runCommand "hyprixe-profile-enabled" { } ''
      export HOME='${enabledHome.home.activationPackage}/home-files'
      unset XDG_CONFIG_HOME
      source "$HOME/.config/uwsm/env-hyprland.d/50-hyprixe.sh"
      test "$XDG_CONFIG_HOME" = '${homeDirectory}/${configDirectory}'
      export XDG_CONFIG_HOME="$HOME/${configDirectory}"
      test ! -e "$XDG_CONFIG_HOME/hypr/hyprland.conf"
      cmp '${canonicalMonitor}' "$XDG_CONFIG_HOME/${monitorFile}"
      cmp '${coreHypr}/hyprland.lua' "$XDG_CONFIG_HOME/hypr/hyprland.lua"
      test -x "$XDG_CONFIG_HOME/hypr/scripts/SessionStartup.sh"
      ${lib.getExe pkgs.bash} -n "$XDG_CONFIG_HOME/hypr/scripts/SessionStartup.sh"
      test -x "$XDG_CONFIG_HOME/hypr/scripts/Wallpaper.sh"
      grep -Fq 'is-active --quiet hyprixe-wallpaper.service &&' "$XDG_CONFIG_HOME/hypr/lua/startup.lua"
      for directive in Requisite After PartOf; do
        grep -Fxq "$directive=graphical-session.target" "$XDG_CONFIG_HOME/${target}"
      done
      grep -Fxq 'Wants=waybar.service hypridle.service swaync.service hyprixe-wallpaper.service hyprixe-polkit.service hyprixe-clipboard.service' "$XDG_CONFIG_HOME/${target}"
      grep -Fxq 'BindsTo=hyprixe-awww.service' "$XDG_CONFIG_HOME/systemd/user/hyprixe-wallpaper.service"
      grep -Fxq 'Upholds=hyprixe-wallpaper.service' "$XDG_CONFIG_HOME/systemd/user/hyprixe-awww.service"
      grep -Fxq 'Before=waybar.service swaync.service hypridle.service hyprixe-polkit.service hyprixe-clipboard.service' "$XDG_CONFIG_HOME/systemd/user/hyprixe-wallpaper.service"
      for unit in waybar.service hyprixe-awww.service hyprixe-wallpaper.service hypridle.service swaync.service hyprixe-polkit.service hyprixe-clipboard.service; do
        grep -Fxq 'PartOf=graphical-session.target' "$XDG_CONFIG_HOME/systemd/user/$unit"
        cmp "$HOME/.config/systemd/user/$unit" "$XDG_CONFIG_HOME/systemd/user/$unit"
      done
      cmp "$HOME/.config/${target}" "$XDG_CONFIG_HOME/${target}"
      cmp ${../../../common/config/wlogout/layout} "$XDG_CONFIG_HOME/wlogout/layout"
      cmp ${../../../common/shell/.p10k.zsh} "$HOME/.p10k.zsh"
      ${lib.getExe pkgs.zsh} -n "$HOME/.zshrc"
      grep -Fqx 'typeset -g GITSTATUS_AUTO_INSTALL=0' "$HOME/.zshrc"
      for script in LockScreen PowerMenu ClipboardWatcher ClipManager ScreenShot; do
        test -x "$XDG_CONFIG_HOME/hypr/scripts/$script.sh"
      done
      test ! -e "$XDG_CONFIG_HOME/dolphinrc"
      test ! -e "$XDG_CONFIG_HOME/kdeglobals"
      test ! -e "$XDG_CONFIG_HOME/Kvantum/kvantum.kvconfig"
      if grep -Eq '@(HYPRIXE_THEME|HYPR_CONFIG|ZSH_AUTOSUGGESTIONS|ZSH_SYNTAX_HIGHLIGHTING)@' \
        "$HOME/.zshrc" "$XDG_CONFIG_HOME/hypr/"*.conf \
        "$XDG_CONFIG_HOME/wlogout/style.css" "$XDG_CONFIG_HOME/swaync/style.css" \
        "$XDG_CONFIG_HOME/systemd/user/"*.service; then
        exit 1
      fi
      session='${hyprland}/share/wayland-sessions/hyprland-uwsm.desktop'
      grep -Fxq 'Name=Hyprland (uwsm-managed)' "$session"
      grep -Fxq 'Exec=${lib.getExe enabled.programs.uwsm.package} start -e -D Hyprland hyprland.desktop' "$session"
      ${lib.getExe pkgs.lua5_4} ${../../../tests/check_lua.lua} "$XDG_CONFIG_HOME"

      bar="$XDG_CONFIG_HOME/hypr/waybar"
      ${lib.getExe pkgs.jq} -e '
        ."custom/distro"."tooltip-format" == "NixOS"
        and ."custom/distro".format == ""
        and ."hyprland/workspaces"."persistent-workspaces"."*" == [1, 2, 3, 4]
        and ."group/traygroup".drawer."click-to-reveal"
        and ."wlr/taskbar"."on-click" == "activate"
        and (.backlight."on-click" | endswith("/bin/hyprixe-brightness-popup\" --toggle"))
      ' "$bar/configs/Frosted-Glass"
      ${lib.getExe pkgs.jq} -e --slurp '
        (.[0]."modules-right" | index("backlight") != null)
        and (.[0]."modules-right" |= map(select(. != "backlight")) | .[0] == .[1])
      ' "$bar/configs/Frosted-Glass" "$bar/configs/Frosted-Glass-no-backlight"
      waybarPalette=$(sed -n 's/^@import "\(.*\)";$/\1/p' "$bar/fallback/style/Frosted-Glass.css")
      test -r "$waybarPalette"
      grep -Fq '${homeDirectory}/.cache-fixture/hyprixe/theme/current/waybar.css' "$bar/style/Frosted-Glass.css"
      grep -Fq '"Symbols Nerd Font Mono"' "$bar/style/Frosted-Glass.css"
      test -x "$(sed -n 's/^geninclude //p' "$XDG_CONFIG_HOME/kitty/kitty.conf")"
      test -r "$(sed -n 's/^@import "\(.*\)"$/\1/p' "$XDG_CONFIG_HOME/hypr/rofi/fallback/wallust/colors-rofi.rasi")"
      if grep -Rq '@HYPRIXE_THEME@' "$bar" "$XDG_CONFIG_HOME/hypr/rofi" "$XDG_CONFIG_HOME/kitty"; then
        exit 1
      fi
      cmp ${../../../common/wallpapers/min_forest.jpg} "$HOME/.data-fixture/hyprixe/wallpapers/min_forest.jpg"
      test -x ${lib.getExe pkgs.awww}
      test -x ${lib.getExe' pkgs.awww "awww-daemon"}
      XDG_CACHE_HOME="$TMPDIR/rofi-cache" ${lib.getExe rofi} \
        -config "$XDG_CONFIG_HOME/hypr/rofi/fallback/config-launcher.rasi" \
        -dump-theme > "$TMPDIR/rofi.rasi"
      grep -Fq 'hyprixe-preview-cover: true;' "$TMPDIR/rofi.rasi"
      ${lib.getExe pkgs.python3} -B - ${../../../common/theme} ${lib.getExe pkgs.kitty} \
        "$XDG_CONFIG_HOME/kitty/kitty.conf" <<'PY'
    import subprocess
    import sys

    resources, kitty, config = sys.argv[1:]
    sys.path.insert(0, resources)
    from engine import KITTY_PARSER

    subprocess.run([kitty, "+runpy", KITTY_PARSER, config], check=True)
    PY
      ${verifyConfig}

      export HOME='${(homeOf enabledDefault).home.activationPackage}/home-files'
      unset XDG_CONFIG_HOME
      test ! -e "$HOME/.config/uwsm/env-hyprland.d/50-hyprixe.sh"
      ${verifyConfig}
      touch "$out"
    '';
  themeEngine = pkgs.runCommand "hyprixe-theme-engine" {
    nativeBuildInputs = [ gtkPython wallust rofi pkgs.kitty pkgs.lua5_4 ];
    FONTCONFIG_FILE = pkgs.makeFontsConf { fontDirectories = [ pkgs.jetbrains-mono ]; };
  } ''
    export HOME="$TMPDIR/home"
    mkdir -p "$HOME"
    test "$(wallust --version)" = 'wallust 3.5.1'
    work="$TMPDIR/source"
    cp -r ${../../..} "$work"
    chmod -R u+rwX "$work"
    cd "$work"
    # The source-only check exercises the checkout guard without requiring Git.
    mkdir .git
    hyprixe-gtk-python - <<'PY'
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import Gio, Gtk, GtkLayerShell

    assert Gtk.CssProvider and Gio.DBusConnection and GtkLayerShell.KeyboardMode.ON_DEMAND
    PY
    for file in test_dynamic_theme.py test_palette_refinement.py test_brightness_popup.py; do
      hyprixe-gtk-python -m unittest discover -s tests -p "$file"
    done
    touch "$out"
  '';
in
{
  checks = {
    profile-disabled = profileDisabled;
    profile-enabled = profileEnabled;
    theme-engine = themeEngine;
    sddm-profiles = greeterCheck;
  };

  sessionVM = pkgs.testers.runNixOSTest (import ./session-vm.nix {
    inherit pkgs username homeDirectory configDirectory rofi gtkPython;
    host = {
      imports = [ (hostModule { importHyprixe = true; }) ];
      home-manager.users.hyprixe-second = {
        imports = [ hyprixe.homeManagerModules.default ];
        home.stateVersion = "26.05";
      };
    };
  });
}
