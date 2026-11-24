# Assets, credits and release checks

The source of detailed attribution is
[CREDITS.md](https://github.com/pixe71/Hyprixe/blob/main/CREDITS.md).
Hyprixe's own integration uses GPL-3.0-or-later; third-party assets retain their
own terms. Keep the notices under `docs/licenses/` with distributed assets.

## KoolDots history

Hyprixe adapted components from KoolDots/LinuxBeginnings and JaKooLit. The unused
`extras/kooldots/` source tree was removed once `common/` became the canonical
Core. Historical credits, active-source headers and applicable licenses remain.

## Wallpaper

`common/wallpapers/min_forest.jpg` is the historical default. The owner's
Pinterest discovery link and matching Senshi/HyDE copies do not establish the
original artist or redistribution permission. Those rights remain unresolved;
do not apply the project's GPL to the artwork or treat screenshots as clearance.
New/replacement wallpapers need their own source, permission and visual review.

Bundled wallpapers are explicitly declared with SHA-256 hashes in
`common/assets/wallpapers.json`. An undeclared file in `common/wallpapers/` makes
deployment fail; manual test images belong in `tests/fixtures/wallpapers/`.
This build-time list does not change the selected wallpaper or theme state.

### Candidate replacements

No candidate is installed. The historical default remains in use until
its rights are verified or a replacement is approved.

- **Original Hyprixe illustration**. Commission or create an original
  panorama with mist-blue ridgelines, a dark evergreen foreground and
  room for the Frosted Glass panels. Retain the editable source and a
  written grant for redistribution under the project's GPL-3.0-or-later
  or another agreed open license. This option still needs artwork and
  approval.
- **Ella Valley cloud forest**. Vyacheslav Argenberg publishes his own
  3072 × 2048 photograph under CC BY 4.0. Keep his requested attribution
  (including VascoPlanet), the source and license links, and identify any
  crop or colour grading. [Author's grant](https://commons.wikimedia.org/wiki/File:Ella_Valley,_Sri_Lanka,_Cloud_forest_in_the_mountains.jpg) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Fog in the morning in Katoomba forest**. Andrea.Messina93 publishes
  their own 1200 × 800 photograph under CC BY-SA 4.0. Credit the author,
  link the source and license, indicate edits and license any adapted
  artwork under CC BY-SA 4.0. The available resolution is lower than
  the historical wallpaper. [Author's grant](https://commons.wikimedia.org/wiki/File:Fog_in_the_morning_in_Katoomba_forest._Blue_Mountains_National_Park,_New_South_Wales.jpg) · [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

An approved replacement must update the product manifest and both profiles'
fallbacks. Keep personal selections intact. Verify that saved references to
the previous bundled file, including collected Nix store paths, resolve to
the new default. Use the recorded digest and the known bundled path to
identify legacy defaults. Keep the Debian baseline as historical evidence
and test the intended difference separately. Verify the fallback palette and
new SDDM snapshots, including rollback. Replace the affected documentation
captures with fresh ones before distribution.

## Kvantum

The Frosted Glass SVG/config pair matches the 2023 Senshi distribution after
line-ending normalization. Its underlying Graphite geometry/config identify
Vince Liuice's GPLv3 component, based on Tsu Jan's KvAdapta work. Preserve the
Vince Liuice, KvAdapta, T-Crypt and compatible Senshi credits/notices.

The Graphite comparison retained all **710 geometric records, 174 distinct
paths and 1,139 Graphite IDs**; 456 config values were unchanged. Frosted Glass
changes affect paint/translucency/blur and selected frame/text settings, rather
than replacing that geometry. The Dolphin variant is Hyprixe's paint derivative,
with `tools/build-dolphin-theme.py` as its generator/source.

These component terms are **GPL-3.0-only**, not a new MIT or automatic
"or later" grant. Keep `Graphite-GPL-3.0.txt` and `Senshi111-MIT.txt` in
`docs/licenses/`. The unused Catppuccin examples were removed with the KoolDots
archive; their historical source records and MIT notice remain preserved.

## Fonts and icons

- Powerlevel10k is MIT; its gitstatus component has a separate GPLv3 notice.
- Symbols Nerd Font Mono retains the pinned Nerd Fonts notice.
- The bundled one-glyph Debian font retains its source/Unlicense notice under
  `common/local/share/fonts/hyprixe/`; Debian trademark rights are not reassigned.
- Hyprixe-authored SDDM user and Wlogout action SVGs use the project license.
- Debian-installed fonts/icons/Qt/KDE retain their package copyright notices.
- The NixOS package adaptations retain the versioned Waybar, Rofi and Wallust
  upstream notices. See the [package attribution table](https://github.com/pixe71/Hyprixe/blob/main/CREDITS.md#nixos-package-adaptations).

Source pins and checksums live with their assets; do not rewrite license texts.

## Screenshots

The current captures under `docs/screenshots/` are listed separately from
the 2026-10-30 historical entries in the asset inventory. Captures 1–3
depict `min_forest.jpg` and remain blocked for redistribution. The current
capture 1 also shows an account, host and local network details.

Captures 4–9 now come from the NixOS VM with project-generated wallpapers.
They cover the desktop, the Rofi launcher and Hyprlock with both palettes.
The asset inventory records the source capture, current hash and previous
hash for each replacement. The only account visible is a disposable VM
fixture account. No embedded PNG metadata was observed.

Before publishing each current capture, check for account names, hostnames,
IP/SSID details, notifications, clipboard/search history, window titles and
image metadata. Clear depicted artwork rights and caption the actual system;
do not fabricate screenshots or claim physical tests from documentation alone.

## Evidence and release checklist

Retained data includes `docs/asset-inventory.json`, `docs/inventory-original.tsv`
and `docs/core-profiles-audit.json`. The asset inventory separates the current
graphics review from its dated historical entries. Older long-form reports
remain in Git history.
Some recorded paths, including `extras/kooldots/`, describe files that have since
been removed; the original inventory entries are intentionally unchanged.
Replacing files clears them from the current tree. Earlier copies are still
reachable through Git history. Review that scope before distributing an
archive that includes history.

Before a release:

- Resolve bundled artwork rights and preserve upstream notices/source.
- Review current screenshots and deliberate public file selection.
- Run [source/dependency/session checks](Maintenance#verify).
- Test real shortcuts, PAM unlock, blur, monitor changes and login transitions.
- Check repeat installation and a safe, previewed backup restoration.
- Record actual versions/results; skipped tests are not successes.

A documentation update does not create or certify a release.
