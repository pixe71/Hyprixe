# Assets, credits and release checks

The source of detailed attribution is
[CREDITS.md](https://github.com/pixe71/hyprixe-debian/blob/main/CREDITS.md).
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

Source pins and checksums live with their assets; do not rewrite license texts.

## Screenshots

Screenshots stay under `docs/screenshots/`; documentation consolidation does not
edit or certify them. The 2026-10-30 review concerned the then-current captures
1–3: capture 1 exposed personal machine/account/network details, while 2–3 had
no observed identifiers. That conclusion does not review later replacements.

Before publishing each current capture, check for account names, hostnames,
IP/SSID details, notifications, clipboard/search history, window titles and
image metadata. Clear depicted artwork rights and caption the actual system;
do not fabricate screenshots or claim physical tests from documentation alone.

## Evidence and release checklist

Retained data: `docs/asset-inventory.json`, `docs/inventory-original.tsv` and
`docs/core-profiles-audit.json`. They are dated audit snapshots, not an automatic
inventory of newly added media. Older long-form reports remain in Git history.
Some recorded paths, including `extras/kooldots/`, describe files that have since
been removed; the original inventory entries are intentionally unchanged.

Before a release:

- Resolve bundled artwork rights and preserve upstream notices/source.
- Review current screenshots and deliberate public file selection.
- Run [source/dependency/session checks](Maintenance#verify).
- Test real shortcuts, PAM unlock, blur, monitor changes and login transitions.
- Check repeat installation and a safe, previewed backup restoration.
- Record actual versions/results; skipped tests are not successes.

A documentation update does not create or certify a release.
