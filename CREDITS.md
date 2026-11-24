# Attribution and provenance

The original repository is commit `f96dfb4` of `pixe71/hyprixe-debian`.
Its complete SHA256 inventory is in `docs/inventory-original.tsv` (593 files).

KoolDots headers identify LinuxBeginnings, GNU GPLv3 and
`SPDX-License-Identifier: GPL-3.0-or-later`. They are preserved in derived
modules and scripts. The integrated configuration files and maintenance
scripts added during this audit are distributed under GPL-3.0-or-later,
subject to the licenses of third-party components. See `LICENSE` for the text.

Hyprixe historically reused and adapted components from KoolDots/LinuxBeginnings.
The former `extras/kooldots/` source tree was removed after `common/` became the
canonical Hyprixe Core. Relevant attribution and applicable licenses are preserved.

The Graphite-derived Frosted Glass and Frosted Glass Dolphin Kvantum pairs
are specifically distributed under **GPL-3.0-only** (version 3), with the
compatible Senshi MIT notice retained. The repository's general "or later"
statement does not broaden the license grant of that inherited component.

Third-party assets retain their own licenses: this statement does not
reassign rights to the wallpaper, icons or illustrations.

| Source | Use / available attribution |
| --- | --- |
| [LinuxBeginnings / KoolDots](https://github.com/LinuxBeginnings/Hyprland-Dots) | Historical base for adapted configuration, scripts and Lua modules in the canonical Hyprixe Core |
| [JaKooLit](https://github.com/JaKooLit/Hyprland-Dots) | Origin of KoolDots and many scripts/themes |
| [Senshi111 / hyprland-hyprdots-files](https://github.com/Senshi111/hyprland-hyprdots-files/tree/c81844d99b835c9bb8bdf1ab8c1ac17b6e2cc448) | The 2023 Frosted Glass Kvantum pair matches Hyprixe after line-ending normalization; its Graphite-derived base remains GPLv3. Theme README credits T-Crypt; root MIT notice, Copyright (c) 2023 Bane, is retained in `docs/licenses/Senshi111-MIT.txt` for compatible contributions/distribution. The wallpaper is also a matching copy, but its artwork rights remain unknown; Pinterest is the owner's discovery reference. |
| [HyDE Frosted Glass](https://github.com/HyDE-Project/hyde-themes/tree/224e1027e451481db526a095242d261d47a68775) | Additional exact copy of min_forest.jpg. This identifies another distributor, not the original artist or an artwork-specific license. |
| [Catppuccin / Kvantum](https://github.com/catppuccin/kvantum/tree/a87694e0a3c97644dbb34f8835112d17b54ace68) | The four former Latte/Mocha Blue SVG/config examples matched this revision after line-ending normalization; config credited elkrien/Arc Dark. These unused examples were removed with the KoolDots archive. Their audit record and MIT notice, Copyright (c) 2021 Catppuccin, remain in `docs/asset-inventory.json` and `docs/licenses/Catppuccin-MIT.txt`. |
| [KDE Dolphin](https://invent.kde.org/system/dolphin), [Baloo Widgets](https://invent.kde.org/libraries/baloo-widgets), [KIO](https://invent.kde.org/frameworks/kio), [Qt](https://doc.qt.io/qt-6/qmainwindow.html) | Native file manager, metadata/previews and Places/Devices model. The inherited Dolphin toolbar and preferences are restored from pre-9259fa5 history. Hyprixe adds only a Dolphin-specific Kvantum paint variant and native KDE color scheme; no generated layout preset remains. |
| [adi1090x/rofi](https://github.com/adi1090x/rofi) | Rofi style 4 layout, attribution preserved |
| [sachatrouve1/Hyprladus](https://github.com/sachatrouve1/Hyprladus/blob/main/config/waybar/config.jsonc) | Functional inspiration for tray grouping and the metrics/distro/clock layout. Its JSONC and CPU script were inspected; no CSS, palette, Powerline dividers, machine paths or scripts are copied. |
| [font-logos](https://github.com/lukas-w/font-logos) | Debian U+F306 glyph, subset from the published font-logos 1.4.0 font and renamed Hyprixe Debian. Unlicense and source SHA256 are included under `common/local/share/fonts/hyprixe/`; Debian's trademark identifies Debian. |
| [Alexays/Waybar](https://github.com/Alexays/Waybar) | MIT-licensed Waybar; optional 0.12 build with a local adaptation of workspace requests to the Lua API, using the same dispatchers as the recent upstream Lua backend |
| [Vladimir-csp/UWSM](https://github.com/Vladimir-csp/uwsm) | Session lifecycle, environment finalization and application scopes; uses Debian's packaged UWSM and Hyprland session entry |
| [romkatv/Powerlevel10k](https://github.com/romkatv/powerlevel10k/tree/v1.20.0) | MIT-licensed prompt; pinned source/checksums in `scripts/shell-sources.json`. Its upstream notice is retained. |
| [romkatv/gitstatus v1.5.4](https://github.com/romkatv/gitstatus/tree/v1.5.4) | Git status daemon/integration with a separate GNU GPLv3 license, not MIT. Powerlevel10k's pinned manifest selects the daemon; the installed `powerlevel10k/gitstatus/LICENSE` retains that notice. |
| [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts/tree/v3.4.0/patched-fonts/NerdFontsSymbolsOnly) | Pinned v3.4.0 Symbols Nerd Font Mono for Kitty private-use glyphs; the upstream font license is installed alongside it. Text remains Debian's JetBrains Mono. |
| [zsh-users/autosuggestions](https://github.com/zsh-users/zsh-autosuggestions), [syntax-highlighting](https://github.com/zsh-users/zsh-syntax-highlighting) | Lightweight plugins installed as official Debian packages, without a plugin manager. |
| [ArtsyMacaw/Wlogout](https://github.com/ArtsyMacaw/wlogout) | MIT-licensed Wayland session menu, installed from Debian stable. Hyprixe supplies its own four-button layout, Frosted Glass CSS and original monochrome SVGs; the Senshi reference informed proportions, not its palette or theme files |
| [SDDM](https://github.com/sddm/sddm) and [Qt Quick](https://doc.qt.io/qt-6/qtquick-index.html) | Greeter platform and Qt 6 controls/effects. The Hyprixe QML layout, glass components and fallback user icon in `common/sddm/themes/hyprixe-frosted/` were authored for this project under GPL-3.0-or-later, using the existing wallpaper; they are not a downloaded third-party theme |
| [Tsu Jan / Kvantum](https://github.com/tsujan/Kvantum/tree/380d6c6940c02434f18e528b61ceeb166624b78f) | Pedram Pourang (Tsu Jan), credited for KvAdapta in the inherited config. Engine source explicitly grants GPL-3.0-or-later; this does not imply an or-later grant for Vince's separately published Graphite derivative. No direct copy of the current KvAdapta SVG was identified. |
| [Vince Liuice / Graphite](https://github.com/vinceliuice/Graphite-kde-theme/tree/3a20a557e824ae4a6b19cc5306e24d5d09aee907) | Confirmed GPLv3 base of both active Frosted Glass files: all 710 SVG geometric records, all 174 distinct path strings and all 1,139 Graphite element IDs retained; 456 unchanged config values. Preserve Vince Liuice/KvAdapta attribution and `docs/licenses/Graphite-GPL-3.0.txt`. The Materia wording in the config describes inspiration, not a separately established source revision. |
| [SherLock707](https://github.com/SherLock707) | Historical Hyprlock/Hypridle contributions in the former KoolDots examples |
| [JosephArmas](https://github.com/JosephArmas) | Optional Rofi calculator |
| [deXPota/kitty-themes](https://github.com/dexpota/kitty-themes) | Reference for the removed collection; no Kitty theme collection is installed |

## NixOS package adaptations

| Source | Use / upstream notice |
| --- | --- |
| [Waybar 0.16.0](https://github.com/Alexays/Waybar/tree/0.16.0) | Upstream source pinned by Nix. The [backlight patch](profiles/nixos/packages/waybar-backlight.patch) adjusts the lower brightness bound and logging for missing devices. [MIT notice](docs/licenses/Waybar-0.16.0-MIT.txt). |
| [Rofi 2.0.0](https://github.com/davatorium/rofi/tree/2.0.0) | Nixpkgs source with Hyprixe's shared launcher adaptation and a worker cleanup fix. [MIT/X11 notice](docs/licenses/Rofi-2.0.0-MIT.txt). |
| [Wallust 3.5.1](https://crates.io/crates/wallust/3.5.1) | Checksummed Cargo release and vendored dependencies. The build patch reports the release version for the shared theme engine. [MIT notice](docs/licenses/Wallust-3.5.1-MIT.txt). |

## Default wallpaper

- File: [`common/wallpapers/min_forest.jpg`](common/wallpapers/min_forest.jpg)
- SHA-256: `9bfb1f796f738ee40a6f072d1cfb5045fb4d46da7af5059de10f405ca284ce30`
- Original author and redistribution terms: unverified.

The owner's [Pinterest discovery link](https://fr.pinterest.com/pin/730427633330946825/)
could not be inspected. The files at the pinned Senshi and HyDE revisions
and in the [sahil-958 collection](https://sahil-958.github.io/walls/hyprdots/Frosted-Glass/min_forest.jpg)
all have the same SHA-256 as the local JPEG. They establish distribution
history. No source located in this review identifies the original artist or
provides an artwork-specific grant that can be relied on for redistribution.

## Test artwork and captures

The two former VM images had verifiable Git history and no verified
redistribution terms. Their replacements are original graphics drawn by the
[fixture generator](tests/fixtures/wallpapers/generate.py). The source and
its graphics are offered under GPL-3.0-or-later. Git history and the status
of the images shown in documentation are recorded in the
[fixture README](tests/fixtures/wallpapers/README.md) and
[asset inventory](docs/asset-inventory.json).

## Publication blockers and asset inventory

The default wallpaper and documentation captures depicting it remain
blocked pending a verified grant or an approved replacement. Review the
affected captures for visible identifiers before distribution.
The [asset inventory](docs/asset-inventory.json) records current hashes,
evidence and uses alongside the separate historical audit. The
[asset guide](docs/wiki/Assets.md) records redistribution conditions and
possible wallpaper replacements. Keep the upstream notices and source for
the Graphite-derived Kvantum assets.

The exact pinned [Nerd Fonts symbols notice](docs/licenses/Nerd-Fonts-Symbols-MIT.txt)
is retained here as well as with the installed font. The bundled Debian glyph
keeps its own [Unlicense](common/local/share/fonts/hyprixe/LICENSE.txt).
Active assets and their attribution are unchanged by the archive cleanup.
