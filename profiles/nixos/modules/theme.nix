{
  config,
  lib,
  pkgs,
  rofi,
  hyprland,
  wallust,
  loginThemeSync,
}:

let
  core = ../../../common/theme;
  python = lib.getExe (import ../packages/gtk-python.nix { inherit pkgs; });
  wallpaperFile = "hyprixe/wallpapers/min_forest.jpg";
  wallpaper = (import ../packages/wallpaper.nix { inherit pkgs; }).image;
  inherit (import ../packages/sddm.nix { inherit pkgs; }) client;
  resources = pkgs.runCommand "hyprixe-theme-resources" { } ''
    mkdir -p "$out/fallback"
    cp -r ${core}/. "$out/"
    ${lib.getExe pkgs.python3} -B - "$out" <<'PY'
    from pathlib import Path
    import sys

    resources = Path(sys.argv[1])
    sys.path.insert(0, str(resources))
    from engine import defaults, render, validate_outputs

    fallback = resources / "fallback"
    for name, text in render(resources, defaults(resources)).items():
        (fallback / name).write_text(text)
    validate_outputs(fallback, native=False)
    PY
  '';
  package = pkgs.writeShellScriptBin "hyprixe-theme" ''
    export PATH=${lib.makeBinPath [
      wallust pkgs.awww hyprland pkgs.procps rofi pkgs.kitty pkgs.lua5_4 pkgs.swaynotificationcenter
    ]}:${lib.optionalString loginThemeSync "${client}/bin:"}"$PATH"
    export HYPRIXE_BUNDLED_WALLPAPER=${wallpaper}
    export HYPRIXE_LOGIN_THEME_SYNC=${if loginThemeSync then "1" else "0"}
    ${lib.optionalString loginThemeSync ''
      if [[ "${"$"}{1:-}" == init ]]; then
        export HYPRIXE_LOGIN_THEME_SYNC=0
      fi
    ''}
    exec ${python} ${../../../common/local/bin/hyprixe-theme} "$@"
  '';
  brightness = pkgs.writeShellScriptBin "hyprixe-brightness-popup" ''
    export PATH=${lib.makeBinPath [ hyprland ]}:"$PATH"
    exec ${python} ${../../../common/local/bin/hyprixe-brightness-popup} "$@"
  '';
in
{
  inherit package brightness;
  fallback = "${resources}/fallback";
  current = "${config.xdg.cacheHome}/hyprixe/theme/current";
  currentWallpaper = "${config.xdg.dataHome}/hyprixe/current-wallpaper";
  defaultWallpaper = "${config.xdg.dataHome}/${wallpaperFile}";
  dataFiles = {
    "hyprixe/theme".source = resources;
    "${wallpaperFile}".source = wallpaper;
  };
}
