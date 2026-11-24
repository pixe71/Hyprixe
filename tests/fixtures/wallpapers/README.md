# Wallpaper fixtures

The NixOS graphical test builds two original landscapes using
[`generate.py`](generate.py) and Pillow from the locked Nixpkgs. The generator
uses integer colour gradients and fixed polygons. It uses no external image,
font, randomness or network input. Its source and the resulting graphics are
offered under GPL-3.0-or-later. Retain the generator, notice and
[license](../../../LICENSE) when redistributing the files.

| VM file | Format and dimensions | Colours | SHA-256 with locked encoders |
| --- | --- | --- | --- |
| `photo-a.jpg` | JPEG, 960 × 540 | Amber and burgundy | `0127bb4156083cc97106d5131b7a5578d5fdbecc198b8ee15df22b0c53246be0` |
| `photo-b.png` | PNG, 800 × 600 | Jade and deep green | `59a3312940dfaeade42e02c395c92149e362be96c4bae30768b46c38185c8858` |

With Python and Pillow, run `python3 tests/fixtures/wallpapers/generate.py /tmp/hyprixe-fixtures`
from the repository root. Use the locked Nixpkgs version to reproduce the
encoded files byte for byte. Local encoder versions can produce different
bytes. The VM tests Wallust extraction, the actual changes of palette and
wallpaper, two image formats and sizes, and an invalid image that must leave
the last valid generation in place. The generated files are in the test
closure. Product wallpapers are the files declared in
[`common/assets/wallpapers.json`](../../../common/assets/wallpapers.json).

## Replaced historical files

Commit `4d1a77d` added the original files for manual tests. Commit
`879f27d` renamed them without changing their bytes. These names describe
Git history.

| Original name | Former fixture | Historical SHA-256 | Provenance |
| --- | --- | --- | --- |
| `wallpaper2.jpg` | `wallpaper_for_test.jpg` | `87ba06cc0614fa328c47b57249132df5836ade365dfdc7d4525aec6693a08019` | Artist, original source and license unverified. |
| `wallpaper3.png` | `rally_car.png` | `486f83884dc5172a9e9dc959f9b0925135bbce6aaac7923ace45db25a2e9f6eb` | XMP identifies a Canva export. The photographer, underlying image source and license are unverified. |
