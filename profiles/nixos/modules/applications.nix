{
  config,
  lib,
  pkgs,
  core,
  theme,
  hyprland,
  systemd,
  uwsm,
  rofi,
}:

let
  inherit (pkgs) kdePackages;
  hypr = core + "/hypr";
  unit = core + "/systemd/user";
  sessionProgram = ../../../common/local/bin/hyprixe-session;
  swaync = pkgs.swaynotificationcenter;
  systemctl = lib.getExe' systemd "systemctl";
  agent = "${kdePackages.polkit-kde-agent-1}/libexec/polkit-kde-authentication-agent-1";
  kvantum = pkgs.qt6Packages.qtstyleplugin-kvantum;
  qtPluginPrefix = pkgs.qt6.qtbase.qtPluginPrefix;
  dolphinPlugins = with kdePackages; [ kio-extras ffmpegthumbs kdegraphics-thumbnailers ] ++ [ kvantum ];
  configHome = config.xdg.configHome;
  shellArg = lib.escapeShellArg;
  themePath = name: "${theme.current}/${name}";
  fallbackPath = name: "${theme.fallback}/${name}";

  render = file: from: to:
    let source = builtins.readFile file;
    in assert lib.hasInfix from source;
    lib.replaceStrings [ from ] [ to ] source;

  lockBase = builtins.readFile (hypr + "/hyprlock.conf");
  renderLock = palette: wallpaper:
    lib.replaceStrings
      [ "@HYPRIXE_THEME@/hyprlock.conf" "$HOME/.local/share/hyprixe/current-wallpaper" ]
      [ palette wallpaper ]
      lockBase;
  lockFallback = pkgs.writeText "hyprixe-hyprlock-fallback.conf" (
    renderLock (fallbackPath "hyprlock.conf") theme.defaultWallpaper
  );
  lockCommand = ''uwsm app -- hyprlock -c "${"$"}{XDG_CONFIG_HOME:-$HOME/.config}/hypr/hyprlock.conf"'';
  lockCommandWithFallback = ''
    lock_config="${"$"}{XDG_CONFIG_HOME:-$HOME/.config}/hypr/hyprlock.conf"
    if [[ ! -r ${shellArg (themePath "hyprlock.conf")} || ! -r ${shellArg theme.currentWallpaper} ]]; then
      lock_config=${lockFallback}
    fi
    ${uwsm} app -- ${lib.getExe pkgs.hyprlock} -c "$lock_config"
  '';
  clipboardConfig = ''rofi_theme="$config_dir/hypr/rofi/config-clipboard.rasi"'';
  clipboardConfigWithFallback = ''
    ${clipboardConfig}
    if [[ ! -r ${shellArg (themePath "rofi.rasi")} ]]; then
      rofi_theme="$config_dir/hypr/rofi/fallback/config-clipboard.rasi"
    fi
  '';

  # Preserve the Core command and its flock/duplicate guard.
  scripts = pkgs.runCommand "hyprixe-session-app-scripts" {
    nativeBuildInputs = [ pkgs.makeWrapper ];
  } ''
    for script in LockScreen PowerMenu ClipboardWatcher ClipManager ScreenShot; do
      install -Dm755 "${hypr}/scripts/$script.sh" "$out/$script.sh"
    done
    patchShebangs --host "$out"
    substituteInPlace "$out/LockScreen.sh" \
      --replace-fail ${shellArg lockCommand} ${shellArg lockCommandWithFallback}
    wrapProgram "$out/LockScreen.sh" --prefix PATH : ${lib.makeBinPath [
      pkgs.util-linux pkgs.procps pkgs.coreutils
    ]}
    wrapProgram "$out/ClipboardWatcher.sh" --prefix PATH : ${lib.makeBinPath [
      pkgs.util-linux pkgs.coreutils pkgs.wl-clipboard pkgs.cliphist
    ]}
    substituteInPlace "$out/ClipManager.sh" \
      --replace-fail ${shellArg clipboardConfig} ${shellArg clipboardConfigWithFallback}
    wrapProgram "$out/ClipManager.sh" --prefix PATH : ${lib.makeBinPath [
      rofi pkgs.cliphist pkgs.wl-clipboard pkgs.libnotify pkgs.procps pkgs.coreutils
    ]}
    wrapProgram "$out/ScreenShot.sh" --prefix PATH : ${lib.makeBinPath [
      pkgs.coreutils pkgs.grim pkgs.slurp pkgs.wl-clipboard pkgs.libnotify pkgs.jq
      pkgs.xdg-user-dirs pkgs.swappy hyprland
    ]}
  '';

  css = application: palette:
    render (core + "/${application}/style.css") "@HYPRIXE_THEME@/${application}.css" palette;
  swayncFallback = pkgs.writeText "hyprixe-swaync-fallback.css" (
    css "swaync" (fallbackPath "swaync.css")
  );
  startSwaync = pkgs.writeShellScript "hyprixe-start-swaync" ''
    style=$1
    if [[ ! -r ${shellArg (themePath "swaync.css")} ]]; then
      style=${swayncFallback}
    fi
    exec ${lib.getExe swaync} --style "$style"
  '';

  wlogoutStyle = palette: lib.replaceStrings [ ''url("icons/'' ] [
    ''url("${core}/wlogout/icons/''
  ] (css "wlogout" palette);
  wlogoutFallback = pkgs.writeText "hyprixe-wlogout-fallback.css" (
    wlogoutStyle (fallbackPath "wlogout.css")
  );
  # Nixpkgs's Wlogout uses GTK 3 without a wrapper for external pixbuf loaders.
  wlogout = pkgs.writeShellScriptBin "wlogout" ''
    export GDK_PIXBUF_MODULE_FILE=${pkgs.librsvg}/${pkgs.gdk-pixbuf.binaryDir}/loaders.cache
    exec ${lib.getExe pkgs.wlogout} "$@"
  '';
  wlogoutCss = "str(config / 'wlogout/style.css')";
  wlogoutCssWithFallback = "(${wlogoutCss} if Path(${builtins.toJSON (themePath "wlogout.css")}).is_file() else '${wlogoutFallback}')";
  confirmationConfig = "str(config / 'hypr/rofi/config.rasi')";
  confirmationConfigWithFallback = "str(config / ('hypr/rofi/config.rasi' if Path(${builtins.toJSON (themePath "rofi.rasi")}).is_file() else 'hypr/rofi/fallback/config.rasi'))";
  session = pkgs.stdenvNoCC.mkDerivation {
    name = "hyprixe-session";
    dontUnpack = true;
    nativeBuildInputs = [ pkgs.makeWrapper ];
    buildInputs = [ pkgs.python3 ];
    installPhase = ''
      install -Dm755 ${sessionProgram} "$out/bin/hyprixe-session"
      patchShebangs --host "$out/bin/hyprixe-session"
      substituteInPlace "$out/bin/hyprixe-session" \
        --replace-fail ${shellArg wlogoutCss} ${shellArg wlogoutCssWithFallback} \
        --replace-fail ${shellArg confirmationConfig} ${shellArg confirmationConfigWithFallback}
      python3 - "$out/bin/hyprixe-session" <<'PY'
    from pathlib import Path
    import sys

    path = Path(sys.argv[1])
    compile(path.read_text(), str(path), "exec")
    PY
      wrapProgram "$out/bin/hyprixe-session" --prefix PATH : ${lib.makeBinPath [
        systemd hyprland rofi wlogout
      ]} --prefix PATH : ${dirOf uwsm}
    '';
    meta.mainProgram = "hyprixe-session";
  };

  dolphin = pkgs.symlinkJoin {
    name = "hyprixe-dolphin";
    paths = [ kdePackages.dolphin ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      wrapProgram "$out/bin/dolphin" \
        --set QT_STYLE_OVERRIDE kvantum \
        --prefix QT_PLUGIN_PATH : ${lib.makeSearchPath qtPluginPrefix dolphinPlugins} \
        --prefix XDG_DATA_DIRS : ${kdePackages.kio-extras}/share:${kdePackages.breeze-icons}/share

      # FileManager1 requests should use the same executable and session.
      unit=share/systemd/user/plasma-dolphin.service
      dbus=share/dbus-1/services
      rm -- "$out/$unit" "$out/$dbus/org.kde.dolphin.FileManager1.service"
      substitute "${kdePackages.dolphin}/$unit" "$out/$unit" \
        --replace-fail 'PartOf=graphical-session.target' \
          "$(printf '%s\n' After=graphical-session.target Requisite=graphical-session.target PartOf=graphical-session.target)" \
        --replace-fail 'ExecStart=${lib.getExe kdePackages.dolphin}' "ExecStart=$out/bin/dolphin"
      substitute "${kdePackages.dolphin}/$dbus/org.kde.dolphin.FileManager1.service" \
        "$out/$dbus/org.freedesktop.FileManager1.service" \
        --replace-fail 'Exec=${lib.getExe kdePackages.dolphin}' "Exec=$out/bin/dolphin"
    '';
  };
  seedKde = pkgs.writeShellScript "hyprixe-kde-defaults" ''
    set -eu
    export PATH=${lib.makeBinPath [ pkgs.coreutils ]}
    # Publish a complete file without replacing a pre-existing file or symlink.
    seed() (
      source=$1 destination=$2
      [[ ! -e "$destination" && ! -L "$destination" ]] || return 0
      directory="${"$"}{destination%/*}"
      [[ "$(realpath -m -- "$directory")" == "$directory" ]] || return 0
      mkdir -p -- "$directory"
      temporary=$(mktemp -- "$directory/.hyprixe-default.XXXXXXXX")
      trap 'rm -f -- "$temporary"' EXIT
      cat -- "$source" > "$temporary"
      if ! ln -T -- "$temporary" "$destination"; then
        [[ -e "$destination" || -L "$destination" ]]
      fi
    )
    seed ${core}/dolphinrc ${shellArg "${configHome}/dolphinrc"}
    seed ${core}/kdeglobals ${shellArg "${configHome}/kdeglobals"}
    seed ${core}/Kvantum/kvantum.kvconfig ${shellArg "${configHome}/Kvantum/kvantum.kvconfig"}
    seed ${../../../common/local/share/kxmlgui5/dolphin/dolphinui.rc} ${shellArg "${config.xdg.dataHome}/kxmlgui5/dolphin/dolphinui.rc"}
  '';

  zshrc =
    let
      source = builtins.readFile ../../../common/shell/.zshrc;
      themeSource = ''"${"$"}{XDG_DATA_HOME:-$HOME/.local/share}/hyprixe/powerlevel10k/powerlevel10k.zsh-theme"'';
    in
    assert lib.hasInfix themeSource source;
    lib.replaceStrings [
      "@ZSH_AUTOSUGGESTIONS@"
      "@ZSH_SYNTAX_HIGHLIGHTING@"
      themeSource
    ] [
      "${pkgs.zsh-autosuggestions}/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
      "${pkgs.zsh-syntax-highlighting}/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
      "${pkgs.zsh-powerlevel10k}/share/zsh-powerlevel10k/powerlevel10k.zsh-theme"
    ] source;

  unitPath = lib.replaceStrings [ "%" ] [ "%%" ] (lib.escape [ "\\" "\"" ] "${configHome}/hypr");
  swayncStylePath = lib.replaceStrings [ "%" ] [ "%%" ] (
    lib.escape [ "\\" "\"" ] "${configHome}/swaync/style.css"
  );
  renderUnit = name: lib.replaceStrings [ "@HYPR_CONFIG@" ] [ unitPath ] (
    builtins.readFile (unit + "/${name}")
  );
  sessionUnit = description: serviceType: ''
    [Unit]
    Description=${description}
    Requisite=graphical-session.target
    After=graphical-session.target hyprixe-wallpaper.service
    PartOf=graphical-session.target

    [Service]
    Type=${serviceType}
    EnvironmentFile=-%t/uwsm/env_session.conf
    Slice=background-graphical.slice
    Restart=on-failure
  '';
in
{
  inherit seedKde;
  packages = [
    dolphin kdePackages.kio-extras kdePackages.kconfig
    kvantum pkgs.hyprlock pkgs.hypridle swaync
    wlogout session pkgs.zsh pkgs.git pkgs.gitstatus
    pkgs.cliphist pkgs.wl-clipboard pkgs.libnotify pkgs.playerctl pkgs.brightnessctl
    pkgs.wireplumber
  ];

  homeFiles = {
    ".zshrc".text = zshrc;
    ".p10k.zsh".source = ../../../common/shell/.p10k.zsh;
  };
  dataFiles = {
    "applications/org.kde.dolphin.desktop".source = "${dolphin}/share/applications/org.kde.dolphin.desktop";
    # Config-level MIME preferences take precedence over data-level defaults.
    "applications/hyprland-mimeapps.list".text = ''
      [Default Applications]
      inode/directory=org.kde.dolphin.desktop;
    '';
  };
  configFiles = {
    "hypr/hyprlock.conf".text = renderLock (themePath "hyprlock.conf") theme.currentWallpaper;
    "hypr/hypridle.conf".text = lib.replaceStrings [
      ''"$HOME/.config/hypr/scripts/LockScreen.sh"''
      "loginctl lock-session"
      "hyprctl dispatch"
    ] [
      (shellArg "${configHome}/hypr/scripts/LockScreen.sh")
      "${lib.getExe' systemd "loginctl"} lock-session"
      "${lib.getExe' hyprland "hyprctl"} dispatch"
    ] (builtins.readFile (hypr + "/hypridle.conf"));
    "swaync/style.css".text = css "swaync" (themePath "swaync.css");
    "wlogout/style.css".text = wlogoutStyle (themePath "wlogout.css");
    "wlogout/layout".source = core + "/wlogout/layout";
    "Kvantum/Frosted-Glass".source = core + "/Kvantum/Frosted-Glass";
    "Kvantum/Frosted-Glass-Dolphin".source = core + "/Kvantum/Frosted-Glass-Dolphin";
  } // lib.genAttrs (map (name: "hypr/scripts/${name}.sh") [
    "LockScreen" "PowerMenu" "ClipboardWatcher" "ClipManager" "ScreenShot"
  ]) (path: { source = "${scripts}/${baseNameOf path}"; });

  units = {
    "hypridle.service" = sessionUnit "Hypridle for the Hyprixe session" "exec" + ''
      ExecStart=${lib.getExe pkgs.hypridle} -c "${unitPath}/hypridle.conf"
    '';
    "swaync.service" = sessionUnit "SwayNC for the Hyprixe session" "dbus" + ''
      BusName=org.freedesktop.Notifications
      ExecStart=${startSwaync} "${swayncStylePath}"
    '';
    "hyprixe-clipboard.service" = renderUnit "hyprixe-clipboard.service";
    "hyprixe-polkit.service" = lib.replaceStrings [
      ''"@HYPR_CONFIG@/scripts/Polkit.sh"''
    ] [ agent ] (builtins.readFile (unit + "/hyprixe-polkit.service"));
  };
}
