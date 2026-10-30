# Asset provenance and publication status

[Documentation index](README.md) · [Credits](../CREDITS.md)

Audit date: **2026-10-30**. The [inventory](asset-inventory.json) records SHA256
and size for all 14 current image/font files and four accompanying Kvantum
configs. Hidden directories and optional examples were included. No image,
font or theme asset was edited, deleted or re-encoded during this audit.
Byte hashes identify files; they do not establish copyright or permission.

## Publication blockers

1. **`wallpapers/min_forest.jpg`**: identical copies and their publishers are
   identified, but the original artwork author and artwork-specific license
   are not. Obtain a reliable license/permission covering redistribution and
   screenshots, or deliberately replace the artwork with a cleared asset.

The former Kvantum blocker A2 is **closed** by the file comparisons and
retained GPLv3 notice below. This does not clear the wallpaper.

Do not apply Hyprixe's GPL license, a collector's license or a theme author's
name to unrelated artwork by inference. The remaining artwork blocker must be resolved for a
public release of the current asset set. Keeping an asset under `extras/`
does not remove its redistribution obligations.

## Wallpaper and Senshi sources

The project owner reports that `wallpapers/min_forest.jpg` was found via
[Pinterest](https://fr.pinterest.com/pin/730427633330946825/).
**Original author: unknown. License: unknown.** The original author and
redistribution license could not be independently verified. This is a
user-provided discovery reference: the pin's contents and relationship to the
matching distribution copies were not independently verified. Recording it
does not clear publication blocker A1.

A confirmed matching distribution copy is available in
[Senshi111/hyprland-hyprdots-files at d9d47fe1](https://github.com/Senshi111/hyprland-hyprdots-files/tree/d9d47fe1c18ed2f1462a3b1dc713169e0abf0337).
Its [theme README](https://github.com/Senshi111/hyprland-hyprdots-files/blob/d9d47fe1c18ed2f1462a3b1dc713169e0abf0337/Theme/README.md)
credits **T-Crypt** for Frosted Glass. Its root
[MIT notice](licenses/Senshi111-MIT.txt) says **Copyright (c) 2023 Bane**.
That notice records the repository's stated terms; it does not prove ownership
of every collected wallpaper or override earlier authors' terms.

| Local asset | Confirmed source and author evidence | Match / modifications | Status |
| --- | --- | --- | --- |
| `wallpapers/min_forest.jpg` | Owner-reported Pinterest discovery above; original author/license unknown. Independently matched [Senshi copy](https://github.com/Senshi111/hyprland-hyprdots-files/blob/d9d47fe1c18ed2f1462a3b1dc713169e0abf0337/Theme/Configs/.config/swww/Frosted-Glass/min_forest.jpg) | Exact 148,096-byte match; SHA256 `9bfb1f796f738ee40a6f072d1cfb5045fb4d46da7af5059de10f405ca284ce30`; no local image modification | **Blocked: artwork rights unconfirmed** |
| `.config/Kvantum/Frosted-Glass/Frosted-Glass.svg` | Exact normalized Senshi copy, derived from Vince Liuice's GPLv3 Graphite light SVG; see the file findings below | All 710 Graphite shape records and 174 distinct paths retained; Frosted styles/gradients predate Hyprixe | **Cleared: GPL-3.0-only; retain attribution and compatible MIT notice** |
| `.config/Kvantum/Frosted-Glass/Frosted-Glass.kvconfig` | Exact normalized Senshi copy; GPLv3 Graphite configuration, retaining its Vince Liuice/KvAdapta author line | 456 unchanged Graphite values, 20 changed, six removed; no added keys | **Cleared: same GPLv3 terms/notices** |
| `.config/Kvantum/Frosted-Glass-Dolphin/Frosted-Glass-Dolphin.svg` and `.kvconfig` | Hyprixe derivative of that GPLv3 pair; [generator](../tools/build-dolphin-theme.py) and [paint guide](dolphin-kvantum.md) | Paint/config changes introduced by `0a92888` and neutral palette `c38e479`, both 2026-10-27; inherited geometry retained | **Cleared: same GPLv3 terms and inherited notices** |

The wallpaper also exactly matches
[HyDE's Frosted Glass image at 224e1027](https://github.com/HyDE-Project/hyde-themes/blob/224e1027e451481db526a095242d261d47a68775/Configs/.config/hyde/themes/Frosted%20Glass/wallpapers/min_forest.jpg).
This is an additional distribution source, not proof of original authorship.
The JPEG has no EXIF or XMP marker, so it provides no embedded attribution.
The HyDE Kvantum files examined are not exact matches; the Senshi pair is.

The same wallpaper is deployed to the desktop, Rofi and Hyprlock, and copied
into the system SDDM theme at installation. Those uses do not create independent
licenses. It is also visible in the supplied screenshots.

## Kvantum file-by-file findings

**Kvantum cleared for v1.0.0.** This conclusion concerns the software theme
pair and its Dolphin derivative; it is independent of wallpaper rights.

### Confirmed content lineage

The matching historical chain is:

```text
Vince Liuice's Graphite light pair, 3a20a557 (2022-09-16), GPLv3
    -> Frosted Glass pair in Senshi, c81844d9 (2023-11-22)
    -> Hyprixe initial commit f96dfb4, same LF-normalized contents
    -> 8e60415 (2026-10-26), line-ending changes only
    -> unchanged original pair in the current checkout
```

This establishes content derivation, not the undocumented download route or
exact moment T-Crypt forked Graphite. The examined Graphite revision predates
the matching Senshi copy. Graphite's SVG has only two path-history commits
(2021-12-19 and 2022-09-16); its later config changes were excluded by comparing
the 2022 pair. The exact fork commit is not needed to identify the licensed
material actually retained.

### Frosted-Glass.kvconfig

Compare the [2022 Graphite config](https://github.com/vinceliuice/Graphite-kde-theme/blob/3a20a557e824ae4a6b19cc5306e24d5d09aee907/Kvantum/Graphite/Graphite.kvconfig)
with the [matching 2023 Senshi config](https://github.com/Senshi111/hyprland-hyprdots-files/blob/c81844d99b835c9bb8bdf1ab8c1ac17b6e2cc448/Theme/Configs/.config/Kvantum/Frosted-Glass/Frosted-Glass.kvconfig).
Graphite has 482 section/key pairs; Frosted Glass retains 476, with **456 values
unchanged, 20 changed, six keys removed and no added keys**. The author line
is identical: Vince Liuice, based on KvAdapta by Tsu Jan.

The rimless Graphite config shares this base, so the config alone does not
identify which packaging variant was used. The paired SVG identifies the
standard light Graphite geometry; the author and GPLv3 terms are the same.

The inherited Frosted changes enable translucency/window and popup blur,
disable state animation, change highlight text/respect-darkness and adjust
toolbar/item-view frames, margins and two item text colours. They already
exist in the 2023 Senshi file. These are pre-Hyprixe theme changes, not edits
made during this audit.

Upstream Graphite SHA256 is
`101060fc99d16c99ab67c4b7af5942b4f1c0192dd7620382fa3d3918c1c9892f`.
Hyprixe's LF-normalized SHA256 is
`095b3d3549a016adc1b5327cf43509eda1d2582bd66632241f7be923928ed5a0`,
identical to the Senshi file and the initial Hyprixe content. The raw checkout
hash, including its CRLF storage, is retained in the JSON inventory.

**Applicable component license: GPL-3.0-only**, using version 3 of the
Graphite grant. Preserve Vince Liuice/Tsu Jan, the Frosted contributor and
Senshi distribution notices. Hyprixe made no semantic changes to this original
file; the separate Dolphin config has its documented Hyprixe paint/settings.

### Frosted-Glass.svg

Compare the [2022 Graphite light SVG](https://github.com/vinceliuice/Graphite-kde-theme/blob/3a20a557e824ae4a6b19cc5306e24d5d09aee907/Kvantum/Graphite/Graphite.svg)
with the [matching 2023 Senshi SVG](https://github.com/Senshi111/hyprland-hyprdots-files/blob/c81844d99b835c9bb8bdf1ab8c1ac17b6e2cc448/Theme/Configs/.config/Kvantum/Frosted-Glass/Frosted-Glass.svg).
The comparison establishes:

- **710/710 geometric records match**: a multiset of SVG shape tag and geometric
  attributes (`d`, coordinates, dimensions, radii, points and transforms),
  excluding paint/editor metadata.
- **174/174 distinct path `d` strings match**, with the same path set.
- **All 1,139 Graphite element IDs remain**. The 55 extra IDs are 25 linear
  gradients, 20 radial gradients and ten gradient stops, not new shape assets.
- Shared-ID differences concern style/gradient references and Inkscape metadata;
  there is **no embedded bitmap image**. This is not an assertion that the whole
  XML or its paint is byte-identical to Graphite.

Graphite SVG SHA256 is
`ea5d8713ad2fce591aca52928aab75c51460a0b28fabb358cd176eabdc06d2fc`.
Hyprixe's LF-normalized SHA256 is
`87ce610c99a6816809ccf9b2a67a6ba1347d17a1708fc726b4ef8f00b27a0083`,
identical to Senshi and the initial Hyprixe SVG. The original pair has no
semantic Git diff from `f96dfb4` to HEAD when ignoring end-of-line whitespace.

**Applicable component license: GPL-3.0-only**, with the same retained names
and notices. The Frosted styling is attributed to T-Crypt by the distributor's
README; Bane is the holder named in its MIT notice, not asserted to be the
original author of the Graphite geometry. No original-pair repaint was made by
Hyprixe. The Dolphin SVG is a Hyprixe paint derivative dated 2026-10-27, under
the same GPLv3 component terms, with its source generator provided.

### Alternative bases checked

| Compared SVG family | Active distinct paths also present | Finding |
| --- | --- | --- |
| Graphite light | 174/174 | Complete geometry and ID correspondence |
| Graphite Dark | 164/174 | Related variant, not the exact retained shape set |
| Layan light/dark | 35/174 and 36/174 | Much weaker match |
| Fluent light/dark | 67/174 | Much weaker match |
| Current KvAdapta light/dark | 0/174 | No direct copy of those SVGs established |
| Archived Catppuccin Latte/Mocha Blue | 0/174 each | Separate MIT assets, no Catppuccin-specific SVG insertion identified |

The active config's entire key set is already present in Graphite. Together
with the complete SVG correspondence, this provides no evidence of a
Catppuccin-specific config/art block incorporated into the active pair. Shared
generic Kvantum keys/rectangles alone are not proof of Catppuccin copying.
Its archived assets keep their own MIT notice; they do not make Frosted Glass MIT.

### Licenses and notices to retain

The [Graphite license at the compared revision](https://github.com/vinceliuice/Graphite-kde-theme/blob/3a20a557e824ae4a6b19cc5306e24d5d09aee907/LICENSE)
is retained verbatim as [Graphite-GPL-3.0.txt](licenses/Graphite-GPL-3.0.txt),
SHA256 `fbbdd5ec489ab07265bcd7ea9072ff0a4f9c539294567ed346fe3cbc612a1aaf`.
Version 3 is the conservative component declaration: do not infer an additional
"or later" grant from the engine's separate license. The
[Kvantum engine source](https://github.com/tsujan/Kvantum/blob/380d6c6940c02434f18e528b61ceeb166624b78f/Kvantum/style/Kvantum.cpp)
explicitly permits GPLv3 or later, and the config retains its earlier KvAdapta
credit; that is not a direct historical SVG match or a relicensing of Vince's
Graphite derivative.

Preserve the inherited author line, Vince Liuice and Tsu Jan/KvAdapta credits,
T-Crypt's Frosted credit, the compatible
[Senshi MIT notice](licenses/Senshi111-MIT.txt) (Copyright 2023 Bane), this
modification/history record and the GPL text. Distribute the actual SVG and
KConfig sources, as this repository does; the Dolphin generator is also available.
Retain [Catppuccin's MIT notice](licenses/Catppuccin-MIT.txt) when distributing
the separate archived Catppuccin files. No theme file or rendering needs to be
changed to carry these notices in the full repository distribution.

## Other vendored assets

| Files | Source / author / stated terms | Local changes and assessment |
| --- | --- | --- |
| `extras/kooldots/catppuccin-latte-blue/catppuccin-latte-blue.svg` and `.kvconfig` | [Catppuccin/Kvantum a87694e0](https://github.com/catppuccin/kvantum/tree/a87694e0a3c97644dbb34f8835112d17b54ace68/themes/catppuccin-latte-blue), Catppuccin; config credits elkrien/Arc Dark; [MIT notice](licenses/Catppuccin-MIT.txt) | Both match that revision after line-ending normalization. No theme edits by this audit; optional, not deployed. Source/notice established. |
| `extras/kooldots/catppuccin-mocha-blue/catppuccin-mocha-blue.svg` and `.kvconfig` | [Same pinned Catppuccin revision](https://github.com/catppuccin/kvantum/tree/a87694e0a3c97644dbb34f8835112d17b54ace68/themes/catppuccin-mocha-blue), same authors/notice | Both match after line-ending normalization; same optional scope. |
| `.local/share/fonts/hyprixe/HyprixeDebian.ttf` | [font-logos](https://github.com/lukas-w/font-logos), published 1.4.0 font, by the font-logos contributors; [bundled Unlicense](../.local/share/fonts/hyprixe/LICENSE.txt) | One-glyph U+F306 subset, renamed Hyprixe Debian. Source font hash and modification are recorded in its [README](../.local/share/fonts/hyprixe/README.md). Debian trademark is not reassigned. |
| `sddm/themes/hyprixe-frosted/assets/user.svg` | Hyprixe repository-authored simple vector icon; GPL-3.0-or-later with the project | Generic head/shoulders primitives; introduced with the own SDDM theme, no external icon pack/source identified. The SDDM wallpaper remains separately blocked. |
| `.config/wlogout/icons/lock.svg`, `logout.svg`, `shutdown.svg`, `reboot.svg` | Hyprixe repository-authored simple monochrome vectors; GPL-3.0-or-later | Introduced with Wlogout, drawn from basic paths/shapes; no Senshi icon assets imported. Senshi inspired proportions, not an imported theme/icon set. |
| `docs/screenshots/screenshot1.png`, `screenshot2.png`, `screenshot3.png` | User-supplied captures; no separate capture license asserted here | Unmodified; review in [screenshot checklist](screenshots/README.md). Capture 1 fails privacy review. Captures 2/3 have no observed personal identifiers, but still contain the uncleared wallpaper. |

## Downloaded and packaged assets

These are not additional vendored image copies in the source tree:

- **Symbols Nerd Font Mono v3.4.0**, upstream commit
  `fa7b859994228a9c8759f99c55a8d31ee92a1b5e`, from
  [Nerd Fonts SymbolsOnly](https://github.com/ryanoasis/nerd-fonts/tree/fa7b859994228a9c8759f99c55a8d31ee92a1b5e/patched-fonts/NerdFontsSymbolsOnly).
  The pinned source/checksum and its [MIT notice](licenses/Nerd-Fonts-Symbols-MIT.txt)
  are verified by installation; the upstream notice is retained with the font.
  No font glyphs are edited by the installer. Its private-use mapping is Kitty-only.
- **Powerlevel10k v1.20.0** is MIT; its **gitstatus v1.5.4** daemon/integration
  has a separate [GNU GPLv3 notice](https://github.com/romkatv/gitstatus/blob/v1.5.4/LICENSE),
  retained at `powerlevel10k/gitstatus/LICENSE` in the prepared installation.
  It must not be described as MIT. Full pins/checksums and installation
  behaviour are in [shell sources](../scripts/shell-sources.json) and
  [Kitty/Zsh](kitty-zsh.md). Neither is attributed as a Hyprixe original.
- **JetBrains Mono, Font Awesome, Breeze icons/cursors, Qt/KDE/SDDM components**
  are installed as Debian packages, not copied into this repository as theme
  artwork. Their package copyright files remain under `/usr/share/doc/`.
  A screenshot can depict their glyphs/icons without making Hyprixe their author.
- Rofi/KoolDots paint/layout is inherited configuration with preserved project
  credits, not a newly imported raster asset. Hyprladus supplied functional
  Waybar inspiration; its CSS/palette/images were not copied.

## Evidence and follow-up

The source URLs are commit-pinned where an exact match was established.
The [font-logos 1.4.0 npm archive](https://registry.npmjs.org/font-logos/-/font-logos-1.4.0.tgz)
also confirms its declared Unlicense and source-font SHA256
`b1368c1cfef326907efb4a76f2f5c1948ccc2f388434ce23473bf50066784de4`.
Comparisons used SHA256 and, only for text SVG/config files, CRLF-to-LF
normalization in memory; local files were never rewritten. Exact upstream
MIT notices and the exact Graphite GPLv3 text are retained under `docs/licenses/`,
without relabeling every asset as MIT. The original project inventory remains unchanged.

To clear a blocker, record the original author, specific source/revision,
applicable license or written permission and required notices. Do not merely
remove the blocker label. Any deliberate replacement artwork/theme must be
reviewed separately for appearance and functionality before the release.
