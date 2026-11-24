{ pkgs, dynamic ? false }:

let
  inherit (pkgs) lib;
  core = ../../../common/sddm;
  name = "hyprixe-frosted";
  wallpaper = import ./wallpaper.nix { inherit pkgs; };
  python = lib.getExe (pkgs.python3.withPackages (ps: [ ps.pillow ]));
  protocol = "${python} -I -B ${core}/sddm_sync.py";
in
{
  inherit name;
  theme = pkgs.runCommand "hyprixe-sddm-${if dynamic then "dynamic" else "static"}" { } ''
    theme="$out/share/sddm/themes/${name}"
    mkdir -p "$theme"
    cp -r ${core}/themes/${name}/. "$theme"
    chmod u+w "$theme/metadata.desktop" "$theme/theme.conf"
    ln -s ${wallpaper.image} "$theme/min_forest.jpg"
    substituteInPlace "$theme/metadata.desktop" \
      --replace-fail 'login screen for Hyprixe Debian' 'login screen for Hyprixe'
    ${lib.optionalString dynamic ''
      substituteInPlace "$theme/theme.conf" \
        --replace-fail 'dynamicPalette=' 'dynamicPalette=file:///var/lib/hyprixe/theme/current/Palette.qml'
    ''}
  '';
  receiver = pkgs.writeShellScriptBin "hyprixe-sddm-sync" ''
    exec ${protocol} serve --idle-timeout 30
  '';
  client = pkgs.writeShellScriptBin "hyprixe-login-theme-sync" ''
    set -euo pipefail
    if [[ $# == 2 && "$1" == ${wallpaper.image} ]]; then
      export PATH=${lib.makeBinPath [ pkgs.coreutils ]}
      umask 077
      temporary=$(mktemp -d -- "${"$"}{XDG_RUNTIME_DIR:-${"$"}{TMPDIR:-/tmp}}/hyprixe-sddm.XXXXXXXX")
      trap 'rm -f -- "$temporary/min_forest.jpg"; rmdir -- "$temporary"' EXIT
      cp -- "$1" "$temporary/min_forest.jpg"
      checksum=$(sha256sum < "$temporary/min_forest.jpg")
      if [[ "${"$"}{checksum%% *}" != ${wallpaper.digest} ]]; then
        echo 'Bundled greeter wallpaper does not match the Core manifest' >&2
        exit 1
      fi
      ${protocol} client "$temporary/min_forest.jpg" "$2"
    else
      exec ${protocol} client "$@"
    fi
  '';
}
