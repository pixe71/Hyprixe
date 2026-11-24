{
  config,
  lib,
  pkgs,
  osConfig ? { },
  ...
}:

let
  core = ../../../common/config;
  hypr = core + "/hypr";
  uwsm = lib.getExe (osConfig.programs.uwsm.package or pkgs.uwsm);
  systemd = osConfig.systemd.package or pkgs.systemd;
  systemctl = lib.getExe' systemd "systemctl";
  hyprland = osConfig.programs.hyprland.package or pkgs.hyprland;
  inherit (import ../packages { inherit pkgs; }) rofi wallust;
  theme = import ./theme.nix {
    inherit config lib pkgs rofi wallust hyprland;
    loginThemeSync = (osConfig.programs.hyprixe.sddm.sync.enable or false)
      && lib.elem config.home.username (osConfig.programs.hyprixe.sddm.sync.users or [ ]);
  };
  desktop = import ./desktop.nix {
    inherit config lib pkgs core uwsm systemd theme hyprland;
  };
  applications = import ./applications.nix {
    inherit config lib pkgs core uwsm systemd theme hyprland rofi;
  };
  sessionUnits = desktop.units // applications.units;
  sessionEnv = lib.concatStringsSep "\n" (lib.filter (
    line: !(lib.hasPrefix ''hl.env("QT_STYLE_OVERRIDE",'' line
      || lib.hasPrefix ''hl.env("QT_QPA_PLATFORMTHEME",'' line)
  ) (lib.splitString "\n" (builtins.readFile (hypr + "/lua/env.lua"))));
  home = config.home.homeDirectory;
  customConfig = config.xdg.configHome != "${home}/.config";
  customXdg = customConfig
    || config.xdg.dataHome != "${home}/.local/share"
    || config.xdg.cacheHome != "${home}/.cache"
    || config.xdg.stateHome != "${home}/.local/state";
  xdgBootstrap = "uwsm/env-hyprland.d/50-hyprixe.sh";
  xdgEnv = pkgs.writeText "hyprixe-uwsm-xdg.sh" ''
    export XDG_CONFIG_HOME=${lib.escapeShellArg config.xdg.configHome}
    export XDG_DATA_HOME=${lib.escapeShellArg config.xdg.dataHome}
    export XDG_CACHE_HOME=${lib.escapeShellArg config.xdg.cacheHome}
    export XDG_STATE_HOME=${lib.escapeShellArg config.xdg.stateHome}
  '';
  themeState = lib.escapeShellArg "${config.xdg.stateHome}/hyprixe/theme.json";
  userDecorations =
    let
      source = builtins.readFile (hypr + "/UserConfigs/user_decorations.lua");
      dynamic = ''pcall(dofile, cache .. "/hyprixe/theme/current/hyprland.lua")'';
    in
    assert lib.hasInfix dynamic source;
    lib.replaceStrings [ dynamic ] [
      ''
        if not ${dynamic} then
          dofile(${builtins.toJSON "${theme.fallback}/hyprland.lua"})
        end
      ''
    ] source;

  luaFiles =
    dir:
    lib.mapAttrs' (name: _: lib.nameValuePair "hypr/${dir}/${name}" {
      source = hypr + "/${dir}/${name}";
    }) (lib.filterAttrs (name: kind: kind == "regular" && lib.hasSuffix ".lua" name) (
      builtins.readDir (hypr + "/${dir}")
    ));

  # Keep only the units available to this profile in the startup transaction.
  sessionTarget = lib.concatStringsSep "\n" (
    map (line:
      if lib.hasPrefix "Wants=" line then
        "Wants=" + lib.concatStringsSep " " (
          lib.filter (name: builtins.hasAttr name sessionUnits) (
            lib.splitString " " (lib.removePrefix "Wants=" line)
          )
        )
      else line
    ) (lib.splitString "\n" (builtins.readFile (core + "/systemd/user/hyprixe-session.target")))
  );
  units = lib.mapAttrs' (
    name: text: lib.nameValuePair "systemd/user/${name}" { source = pkgs.writeText name text; }
  ) (sessionUnits // { "hyprixe-session.target" = sessionTarget; });

  sessionStartup = pkgs.runCommand "hyprixe-SessionStartup.sh" { } ''
    install -m755 ${hypr}/scripts/SessionStartup.sh "$out"
    patchShebangs --host "$out"
    substituteInPlace "$out" \
      --replace-fail 'mkdir -p' '${lib.getExe' pkgs.coreutils "mkdir"} -p' \
      --replace-fail 'flock -n' '${lib.getExe' pkgs.util-linux "flock"} -n' \
      --replace-fail 'uwsm check' '${uwsm} check' \
      --replace-fail 'uwsm finalize' '${uwsm} finalize' \
      --replace-fail 'systemctl --user' '${systemctl} --user'
  '';

  # Preserve the hotplug callback and run it once the wallpaper service is installed and active.
  hotplugGate = "systemctl --user is-active --quiet graphical-session.target && ";
  startupLua =
    let
      source = builtins.readFile (hypr + "/lua/startup.lua");
    in
    assert lib.hasInfix hotplugGate source;
    lib.replaceStrings [ hotplugGate ] [
      "${systemctl} --user is-active --quiet graphical-session.target && ${systemctl} --user is-active --quiet hyprixe-wallpaper.service && "
    ] source;
in
{
  options.programs.hyprixe.enable = lib.mkEnableOption "the Hyprixe Home Manager session files";

  config = lib.mkIf config.programs.hyprixe.enable {
    assertions = [
      {
        assertion = osConfig == { } || (
          (osConfig.programs.hyprland.enable or false)
          && (osConfig.programs.hyprland.withUWSM or false)
          && ((osConfig.security.pam.services or { }) ? hyprlock)
        );
        message = "The Hyprixe Home Manager session requires NixOS Hyprland with UWSM and Hyprlock PAM. Enable the Hyprixe system module or provide these settings in the host.";
      }
      {
        assertion = !config.wayland.windowManager.hyprland.enable;
        message = "Hyprixe manages hyprland.lua. Disable Home Manager's wayland.windowManager.hyprland module.";
      }
      {
        assertion = !(config.xdg.configFile ? "hypr/hyprland.conf");
        message = "Hyprixe uses hyprland.lua. Remove the Home Manager declaration for hypr/hyprland.conf.";
      }
      {
        assertion = !config.programs.waybar.enable && !config.programs.waybar.systemd.enable;
        message = "Hyprixe manages Waybar's configuration and service. Disable Home Manager's programs.waybar module.";
      }
      {
        assertion = !config.programs.kitty.enable && !config.programs.hyprlock.enable;
        message = "Hyprixe manages Kitty and Hyprlock configuration. Disable Home Manager's programs.kitty and programs.hyprlock modules.";
      }
      {
        assertion = !config.services.hypridle.enable && !(osConfig.services.hypridle.enable or false);
        message = "Hyprixe owns hypridle.service. Disable the host's NixOS/Home Manager Hypridle modules, including programs.hyprlock.enable on NixOS.";
      }
      {
        assertion = !config.services.swaync.enable && !config.services.cliphist.enable;
        message = "Hyprixe owns the notification and clipboard services. Disable Home Manager's SwayNC and Cliphist modules.";
      }
      {
        assertion = !config.programs.zsh.enable;
        message = "Hyprixe deploys its canonical .zshrc. Disable Home Manager's programs.zsh module for this user.";
      }
    ];

    fonts.fontconfig.enable = true;
    home.packages = desktop.packages ++ applications.packages ++ [ theme.package theme.brightness wallust ];
    xdg.dataFile = theme.dataFiles // applications.dataFiles;
    home.activation.hyprixeInitialTheme = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
      if [[ ! -e ${themeState} && ! -L ${themeState} ]]; then
        (
          source ${xdgEnv}
          run ${lib.getExe theme.package} init
        )
      fi
    '';
    home.activation.hyprixeKdeDefaults = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
      run ${applications.seedKde}
    '';
    xdg.configFile = luaFiles "lua" // luaFiles "UserConfigs" // desktop.configFiles // applications.configFiles // units // {
      "hypr/hyprland.lua".source = hypr + "/hyprland.lua";
      "hypr/profile.lua".source = hypr + "/profile.lua";
      "hypr/lua/startup.lua".text = startupLua;
      "hypr/lua/env.lua".text = sessionEnv;
      "hypr/UserConfigs/user_decorations.lua".text = userDecorations;
      "hypr/scripts/SessionStartup.sh".source = sessionStartup;
    } // lib.optionalAttrs customXdg {
      "${xdgBootstrap}".source = xdgEnv;
    };

    home.file = applications.homeFiles // lib.optionalAttrs customConfig ({
      # UWSM can discover the custom root from a login still using the XDG default.
      ".config/${xdgBootstrap}".source = xdgEnv;
    } // lib.mapAttrs' (path: file: lib.nameValuePair ".config/${path}" file) units);
  };
}
