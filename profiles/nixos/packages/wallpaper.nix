{ pkgs }:

let
  repo = ../../..;
  manifest = builtins.fromJSON (builtins.readFile (repo + "/common/assets/wallpapers.json"));
  entry = pkgs.lib.findFirst (file: file.file == "min_forest.jpg")
    (throw "Missing bundled Hyprixe wallpaper") manifest.files;
in
{
  digest = entry.sha256;
  image = pkgs.runCommand "hyprixe-min_forest.jpg" {
    nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ ps.pillow ])) ];
  } ''
    python3 -B - "${repo}" "$out" <<'PY'
    from pathlib import Path
    import shutil
    import sys

    root, output = map(Path, sys.argv[1:])
    sys.path[:0] = [str(root / "scripts"), str(root / "common/theme")]
    from engine import image_valid
    from source_layout import shipping_wallpapers

    image = next(path for path in shipping_wallpapers(root) if path.name == "min_forest.jpg")
    shutil.copyfile(image_valid(image), output)
    PY
  '';
}
