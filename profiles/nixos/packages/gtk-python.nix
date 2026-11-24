{ pkgs }:

let
  python = pkgs.python3.withPackages (ps: [ ps.pillow ps.pygobject3 ]);
in
pkgs.runCommand "hyprixe-gtk-python" {
  nativeBuildInputs = [ pkgs.wrapGAppsHook3 pkgs.gobject-introspection ];
  buildInputs = [ pkgs.gtk3 pkgs.gtk-layer-shell ];
  dontWrapGApps = true;
  meta.mainProgram = "hyprixe-gtk-python";
} ''
  mkdir -p "$out/bin"
  gappsWrapperArgsHook
  makeWrapper ${pkgs.lib.getExe python} "$out/bin/hyprixe-gtk-python" \
    "${"$"}{gappsWrapperArgs[@]}" --set PYTHONDONTWRITEBYTECODE 1
''
