# Attribution and provenance

The original repository is commit `f96dfb4` of `pixe71/hyprixe-debian`.
Its complete SHA256 inventory is in `docs/inventory-original.tsv` (593 files).

KoolDots headers identify LinuxBeginnings, GNU GPLv3 and
`SPDX-License-Identifier: GPL-3.0-or-later`. They are preserved in derived
modules and scripts. The integrated configuration files and maintenance
scripts added during this audit are distributed under GPL-3.0-or-later,
subject to the licenses of third-party components. See `LICENSE` for the text.

Third-party assets retain their own licenses: this statement does not
reassign rights to the wallpaper, icons or illustrations.

| Source | Use / available attribution |
| --- | --- |
| [LinuxBeginnings / KoolDots](https://github.com/LinuxBeginnings/Hyprland-Dots) | Base configuration, scripts and Lua modules, optional library |
| [JaKooLit](https://github.com/JaKooLit/Hyprland-Dots) | Origin of KoolDots and many scripts/themes |
| Senshi | Frosted Glass theme and Dolphin adaptations according to the original repository's author; exact URL/version/license absent from the received repository |
| [KDE Dolphin](https://invent.kde.org/system/dolphin), [Baloo Widgets](https://invent.kde.org/libraries/baloo-widgets), [KIO](https://invent.kde.org/frameworks/kio), [Qt](https://doc.qt.io/qt-6/qmainwindow.html) | Native file manager, metadata/previews, Places/Devices model and dock-state format. Hyprixe adapts the inherited Dolphin toolbar and preferences; the layout preset is generated with standard Qt APIs. The original toolbar remains documented in the inventory rather than presented as unmodified. |
| [adi1090x/rofi](https://github.com/adi1090x/rofi) | Rofi style 4 layout, attribution preserved |
| [Alexays/Waybar](https://github.com/Alexays/Waybar) | MIT-licensed Waybar; optional 0.12 build with a local adaptation of workspace requests to the Lua API, using the same dispatchers as the recent upstream Lua backend |
| [Vladimir-csp/UWSM](https://github.com/Vladimir-csp/uwsm) | Session lifecycle, environment finalization and application scopes; uses Debian's packaged UWSM and Hyprland session entry |
| [SDDM](https://github.com/sddm/sddm) and [Qt Quick](https://doc.qt.io/qt-6/qtquick-index.html) | Greeter platform and Qt 6 controls/effects. The Hyprixe QML layout, glass components and fallback user icon in `sddm/themes/hyprixe-frosted/` were authored for this project under GPL-3.0-or-later, using the existing wallpaper; they are not a downloaded third-party theme |
| [Tsu Jan / Kvantum](https://github.com/tsujan/Kvantum) | Kvantum engine and KvAdapta base mentioned in the theme |
| [Vince / vinceliuice](https://github.com/vinceliuice) | Author named in Frosted-Glass.kvconfig, Materia theme base |
| [SherLock707](https://github.com/SherLock707) | Historical Hyprlock/Hypridle contributions, preserved in the examples |
| [JosephArmas](https://github.com/JosephArmas) | Optional Rofi calculator |
| [deXPota/kitty-themes](https://github.com/dexpota/kitty-themes) | Reference for the removed collection; no Kitty theme collection is installed |

The “Senshi” URL and wallpaper license must be confirmed from the source
provided by its author before redistributing the assets independently.
The audit does not invent a repository or license to fill this gap.
Already tracked assets remain preserved; no original attribution was removed.
