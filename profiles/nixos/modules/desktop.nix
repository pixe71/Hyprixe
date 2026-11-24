{
  config,
  lib,
  pkgs,
  core,
  hyprland,
  uwsm,
  systemd,
  theme,
}:

let
  hypr = core + "/hypr";
  unit = core + "/systemd/user";
  inherit (import ../packages { inherit pkgs; }) rofi waybar;
  python = lib.getExe pkgs.python3;
  kitty = lib.getExe pkgs.kitty;
  kittyPalette = pkgs.writeShellScript "hyprixe-kitty-palette" ''
    palette=${lib.escapeShellArg "${theme.current}/kitty.conf"}
    if [[ ! -r "$palette" ]]; then
      palette=${lib.escapeShellArg "${theme.fallback}/kitty.conf"}
    fi
    exec ${lib.getExe' pkgs.coreutils "cat"} "$palette"
  '';
  configPath = "${config.xdg.configHome}/hypr";

  bar = builtins.fromJSON (builtins.readFile (hypr + "/waybar/configs/Frosted-Glass"));
  barSettings = bar // {
    "custom/distro" = bar."custom/distro" // {
      format = "";
      tooltip-format = "NixOS";
    };
    "custom/temperature" = bar."custom/temperature" // {
      exec = lib.replaceStrings [ "python3 " ] [ "${python} " ] bar."custom/temperature".exec;
    };
    backlight = bar.backlight // {
      on-click = ''"${lib.getExe theme.brightness}" --toggle'';
    };
    bluetooth = removeAttrs bar.bluetooth [ "on-click" ];
    network = removeAttrs bar.network [ "on-click" ];
    pulseaudio = removeAttrs bar.pulseaudio [ "on-click" "on-click-right" ];
  };
  barJson = pkgs.writeText "hyprixe-waybar.json" (builtins.toJSON barSettings);
  barJsonWithoutBacklight = pkgs.writeText "hyprixe-waybar-no-backlight.json" (builtins.toJSON (
    barSettings // { "modules-right" = lib.remove "backlight" barSettings."modules-right"; }
  ));
  waybarConfig = pkgs.runCommand "hyprixe-waybar-config" { } ''
    install -Dm644 ${barJson} "$out/configs/Frosted-Glass"
    install -Dm644 ${barJsonWithoutBacklight} "$out/configs/Frosted-Glass-no-backlight"
    install -Dm644 ${hypr}/waybar/scripts/temperature.py "$out/scripts/temperature.py"
    render_style() {
      local root=$1 palette=$2
      install -Dm644 ${hypr}/waybar/style.css "$root/style.css"
      install -Dm644 ${hypr}/waybar/style/Frosted-Glass.css "$root/style/Frosted-Glass.css"
      substituteInPlace "$root/style/Frosted-Glass.css" \
        --replace-fail '"@HYPRIXE_THEME@/waybar.css"' "$palette" \
        --replace-fail 'Hyprixe Debian' 'Symbols Nerd Font Mono'
    }
    render_style "$out" ${lib.escapeShellArg (builtins.toJSON "${theme.current}/waybar.css")}
    render_style "$out/fallback" ${lib.escapeShellArg (builtins.toJSON "${theme.fallback}/waybar.css")}
  '';
  startWaybar = pkgs.writeShellScript "hyprixe-start-waybar" ''
    root=$1
    settings="$root/configs/Frosted-Glass"
    style="$root/style.css"
    if [[ ! -r ${lib.escapeShellArg "${theme.current}/waybar.css"} ]]; then
      style="$root/fallback/style.css"
    fi
    # Waybar 0.16 also detects keyboard LEDs. Show the screen control only
    # when a screen backlight exists.
    for device in /sys/class/backlight/*; do
      if [[ -r "$device/max_brightness" ]] && read -r max < "$device/max_brightness" &&
          [[ "$max" =~ ^[0-9]*[1-9][0-9]*$ ]]; then
        exec ${lib.getExe waybar} -c "$settings" -s "$style"
      fi
    done
    exec ${lib.getExe waybar} -c "$settings-no-backlight" -s "$style"
  '';
  rofiConfig = pkgs.runCommand "hyprixe-rofi-config" { } ''
    render_rofi() {
      local root=$1 palette=$2 wallpaper=$3
      mkdir -p "$root"
      cp -r ${hypr}/rofi/. "$root/"
      chmod -R u+w "$root"
      substituteInPlace "$root/config.rasi" \
        --replace-fail '"uwsm app -- {cmd}"' '"${uwsm} app -- {cmd}"' \
        --replace-fail 'terminal: "kitty"' 'terminal: "${kitty}"'
      substituteInPlace "$root/wallust/colors-rofi.rasi" \
        --replace-fail '"@HYPRIXE_THEME@/rofi.rasi"' "$palette"
      substituteInPlace "$root/themes/Frosted-Glass-Launcher.rasi" \
        --replace-fail '"$HOME/.local/share/hyprixe/current-wallpaper"' "$wallpaper"
    }
    render_rofi "$out" ${lib.escapeShellArg (builtins.toJSON "${theme.current}/rofi.rasi")} \
      ${lib.escapeShellArg (builtins.toJSON theme.currentWallpaper)}
    render_rofi "$out/fallback" ${lib.escapeShellArg (builtins.toJSON "${theme.fallback}/rofi.rasi")} \
      ${lib.escapeShellArg (builtins.toJSON theme.defaultWallpaper)}
  '';
  selectRofiConfig = ''
    rofi_root="$hypr/rofi"
    if [[ ! -r ${lib.escapeShellArg "${theme.current}/rofi.rasi"} || ! -r ${lib.escapeShellArg theme.currentWallpaper} ]]; then
      rofi_root="$rofi_root/fallback"
    fi
  '';
  rofiConfigRoot = ''hypr="${"$"}{XDG_CONFIG_HOME:-$HOME/.config}/hypr"'';
  scripts = pkgs.runCommand "hyprixe-desktop-scripts" {
    nativeBuildInputs = [ pkgs.makeWrapper ];
  } ''
    for script in LaunchApp LaunchTerminal RofiLauncher WindowSwitcher Wallpaper WallpaperDaemon; do
      install -Dm755 "${hypr}/scripts/$script.sh" "$out/$script.sh"
    done
    patchShebangs --host "$out"

    substituteInPlace "$out/LaunchApp.sh" --replace-fail 'exec uwsm app' 'exec ${uwsm} app'
    substituteInPlace "$out/LaunchTerminal.sh" \
      --replace-fail 'exec uwsm app -- kitty' 'exec ${uwsm} app -- ${kitty}'
    substituteInPlace "$out/RofiLauncher.sh" \
      --replace-fail 'export PATH="$HOME/.local/bin:$PATH"' ':' \
      --replace-fail ${lib.escapeShellArg rofiConfigRoot} ${lib.escapeShellArg (rofiConfigRoot + "\n" + selectRofiConfig)} \
      --replace-fail '$hypr/rofi/config-launcher.rasi' '$rofi_root/config-launcher.rasi' \
      --replace-fail 'uwsm app -t scope -- rofi' '${uwsm} app -t scope -- ${lib.getExe rofi}'
    substituteInPlace "$out/WindowSwitcher.sh" \
      --replace-fail 'export PATH="$HOME/.local/bin:$PATH"' ':' \
      --replace-fail ${lib.escapeShellArg rofiConfigRoot} ${lib.escapeShellArg (rofiConfigRoot + "\n" + selectRofiConfig)} \
      --replace-fail '$hypr/rofi/config-windows.rasi' '$rofi_root/config-windows.rasi' \
      --replace-fail 'rofi -hyprixe-launcher' '${lib.getExe rofi} -hyprixe-launcher' \
      --replace-fail 'hyprctl jq rofi' 'hyprctl jq'
    wrapProgram "$out/WindowSwitcher.sh" --prefix PATH : ${lib.makeBinPath [ hyprland pkgs.jq ]}
    substituteInPlace "$out/WallpaperDaemon.sh" --replace-fail 'exec awww-daemon' \
      'exec ${lib.getExe' pkgs.awww "awww-daemon"}'
    substituteInPlace "$out/Wallpaper.sh" \
      --replace-fail 'awww-daemon 9>&- >>"$state/wallpaper.log" 2>&1 &' 'exit 1' \
      --replace-fail 'exec "${"$"}{HOME}/.local/bin/hyprixe-theme" restore' \
        'exec "${lib.getExe theme.package}" restore'
    wrapProgram "$out/Wallpaper.sh" --prefix PATH : ${lib.makeBinPath [
      pkgs.awww hyprland pkgs.jq pkgs.coreutils pkgs.gnugrep pkgs.util-linux systemd
    ]} --prefix PATH : ${dirOf uwsm}
  '';

  unitPath = lib.replaceStrings [ "%" ] [ "%%" ] (lib.escape [ "\\" "\"" ] configPath);
  renderUnit = lib.replaceStrings [ "@HYPR_CONFIG@" "@WAYBAR_EXEC@" ] [
    unitPath
    "${startWaybar}"
  ];
in
{
  packages = [
    pkgs.awww
    pkgs.kitty
    pkgs.jetbrains-mono
    pkgs.nerd-fonts.symbols-only
    pkgs.font-awesome_4
    pkgs.kdePackages.breeze-icons
  ];
  configFiles = {
    "hypr/profile.env".source = hypr + "/profile.env";
    "hypr/waybar".source = waybarConfig;
    "hypr/rofi".source = rofiConfig;
    "kitty/kitty.conf".text = lib.replaceStrings [ "include @HYPRIXE_THEME@/kitty.conf" ] [
      "geninclude ${kittyPalette}"
    ] (builtins.readFile (core + "/kitty/kitty.conf")) + ''

      shell ${lib.getExe pkgs.zsh}
    '';
  } // lib.genAttrs (map (name: "hypr/scripts/${name}.sh") [
    "LaunchApp"
    "LaunchTerminal"
    "RofiLauncher"
    "WindowSwitcher"
    "Wallpaper"
    "WallpaperDaemon"
  ]) (path: { source = "${scripts}/${baseNameOf path}"; });

  units = {
    # The daemon can restart without a monitor event. Reapply the selected
    # wallpaper each time it becomes available, with the oneshot tied to it.
    "hyprixe-awww.service" = renderUnit (lib.replaceStrings [
      "Description=Hyprixe wallpaper daemon\n"
    ] [ "Description=Hyprixe wallpaper daemon\nUpholds=hyprixe-wallpaper.service\n" ] (
      builtins.readFile (unit + "/hyprixe-awww.service")
    ));
    "hyprixe-wallpaper.service" = renderUnit (lib.replaceStrings [
      "Requires=hyprixe-awww.service"
    ] [ "BindsTo=hyprixe-awww.service" ] (builtins.readFile (unit + "/hyprixe-wallpaper.service")));
    "waybar.service" = renderUnit (lib.replaceStrings [
      "[Unit]\n"
      "ExecStart=\n"
      ''-c "@HYPR_CONFIG@/waybar/configs/Frosted-Glass" -s "@HYPR_CONFIG@/waybar/style.css"''
    ] [
      ''
        [Unit]
        Description=Waybar for the Hyprixe session
        Requisite=graphical-session.target
        After=graphical-session.target
        PartOf=graphical-session.target
      ''
      ""
      ''"@HYPR_CONFIG@/waybar"''
    ] (builtins.readFile (unit + "/waybar.service.d/hyprixe.conf")));
  };
}
