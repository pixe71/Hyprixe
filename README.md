# Hyprixe Debian — Frosted Glass

Configuration Debian 13 / Hyprland issue de KoolDots, adaptée à Alacritty et Dolphin.
Le profil principal utilise les pilotes graphiques du PC. Un profil VMware distinct
conserve les adaptations de rendu logiciel nécessaires aux anciens essais.

Le thème conserve le wallpaper `min_forest.jpg`, le verre translucide bleu/cyan,
le blur, les arrondis de 13 px, les bordures bleues/violettes, Waybar en haut et
le thème Kvantum Frosted-Glass. Les fichiers SVG/Kvantum, le wallpaper et la toolbar
Dolphin d’origine sont conservés octet pour octet.

![Wallpaper Frosted Glass](wallpapers/min_forest.jpg)

Les captures de la session sur machine physique sont à ajouter dans
[`docs/screenshots/`](docs/screenshots/README.md). L’image ci-dessus est le wallpaper,
pas une capture d’une session validée.

## Installation rapide

Cible : **Debian 13**, **Hyprland 0.56.2 avec configuration Lua** (version
fonctionnelle indiquée par l’utilisateur, API vérifiée au tag upstream v0.56.2).
**0.55.2 est la version minimale acceptée par l’installateur**, pas une version
imposée : 0.56.2 est acceptée. Les versions futures demandent leur propre contrôle.
Utiliser un compte utilisateur avec `sudo` et un pilote GPU opérationnel.

```bash
git clone https://github.com/pixe71/hyprixe-debian.git
cd hyprixe-debian
./install.sh                 # native par défaut
# ou : ./install.sh vmware
```

L’installateur installe les dépendances Debian, active les backports officiels si
nécessaire, prépare Rofi Wayland 2.0.0 / awww 0.12.1 et un Waybar compatible IPC Lua
si nécessaire, puis sauvegarde et
déploie les fichiers utilisateur. La première compilation peut prendre plusieurs
minutes et télécharger les outils C/Rust. Lire [INSTALL.md](INSTALL.md) pour les
prérequis, les effets système, les sauvegardes, la restauration et les contrôles.

Waybar 0.12 de Debian utilise encore l’ancien IPC pour les clics sur les workspaces.
L’installateur réutilise un Waybar doté du support Lua ou compile la même base
0.12 avec une adaptation limitée de ces requêtes. La disposition et le thème de
la barre restent identiques. Voir le contrôle 0.56.2 dans `docs/VALIDATION.md`.

```bash
./install.sh --dry-run       # aperçu, sans APT ni copie de configuration
./install.sh --no-packages   # dépendances déjà présentes, vérifiées avant copie
./verify.sh                 # contrôles statiques et tests dans un HOME temporaire
./uninstall.sh --list
./uninstall.sh --dry-run
./uninstall.sh              # annule la dernière transaction non restaurée
```

## Composants

Hyprland et les modules Lua KoolDots, Alacritty, Dolphin, Kvantum/Qt6, Waybar,
Rofi Wayland, Hyprlock, Hypridle, awww, PipeWire/WirePlumber, NetworkManager,
Blueman, SwayNC et cliphist. Les icônes utilisent Breeze et FontAwesome ; la
police JetBrains Mono est disponible dans Debian.

## Raccourcis

Clavier par défaut : français AZERTY `fr/latin9`. Les workspaces utilisent les
codes physiques de la rangée supérieure, indépendamment des chiffres AZERTY.

| Raccourci | Action |
| --- | --- |
| SUPER + Return | Alacritty |
| SUPER + E | Dolphin |
| SUPER + Space | Rofi |
| SUPER + Q | Fermer la fenêtre |
| SUPER + L | Hyprlock |
| SUPER + clic gauche / droit | Déplacer / redimensionner |
| SUPER + flèches | Déplacer le focus |
| SUPER + SHIFT + flèches | Déplacer la fenêtre |
| SUPER + CTRL + flèches | Redimensionner par pas de 50 px |
| SUPER + touches 1–0, positions physiques | Workspaces 1–10 |
| SUPER + SHIFT + touches 1–0 | Envoyer la fenêtre au workspace |
| SUPER + PageUp / PageDown ou molette | Workspace précédent / suivant |
| SUPER + F / SHIFT + F | Plein écran / maximiser |
| SUPER + V | Floating |
| SUPER + P / J | Pseudo / inversion du split dwindle |
| ALT + Tab / ALT + SHIFT + Tab | Fenêtre suivante / précédente du workspace courant |
| ALT + F10 | Sélecteur Rofi de toutes les fenêtres |
| SUPER + CTRL + V | Historique du presse-papiers |
| SUPER + Print / SHIFT + Print | Capture entière / zone |
| SUPER + SHIFT + E | Menu session/power |

Touches multimédia et luminosité conservées. Un geste horizontal à trois doigts
change le workspace. Il n’y a qu’une source de raccourcis actifs :
`.config/hypr/lua/keybinds.lua`. Les ajouts personnels sont chargés ensuite depuis
`UserConfigs/user_keybinds.lua` ; aucun fichier de `extras/` ne les écrase.

## Profils et organisation

```text
.config/                  configuration active, native par défaut
.local/share/kxmlgui5/    toolbar Dolphin (chemin également utilisé par KF6)
wallpapers/               image Frosted Glass unique
profiles/native/          aucun forçage graphique
profiles/vmware/           rendu logiciel explicite, exemples d’écrans facultatifs
extras/kooldots/           bibliothèque upstream facultative, jamais installée
scripts/                  déploiement, dépendances, validation
tests/                    tests isolés ; aucune session graphique simulée comme réelle
docs/                     audit, inventaire original et validations
install.sh / uninstall.sh / verify.sh
packages*.txt
```

Les profils partagent le thème, les raccourcis SUPER et la détection des écrans.
Le profil VMware ajoute les variables Mesa de rendu logiciel et le curseur
logiciel. Il ne force aucune résolution ; les exemples `Virtual-1` ne sont pas
installés. Un changement de profil demande une reconnexion pour renouveler
l’environnement des applications.

## Crédits

- [KoolDots / LinuxBeginnings](https://github.com/LinuxBeginnings/Hyprland-Dots),
  issu des [dotfiles de JaKooLit](https://github.com/JaKooLit/Hyprland-Dots) :
  base Lua, scripts, animations et bibliothèque de configurations. Les en-têtes
  GPL-3.0-or-later sont conservés.
- Senshi : inspiration et fichiers Frosted Glass/Dolphin indiqués par le dépôt
  initial et son auteur. Le dépôt initial n’inclut pas d’URL de provenance précise
  ni de licence du wallpaper ; voir [CREDITS.md](CREDITS.md).
- [adi1090x/rofi](https://github.com/adi1090x/rofi) : disposition Rofi, reprise via KoolDots.
- [Kvantum / Tsu Jan](https://github.com/tsujan/Kvantum), KvAdapta et Vince/Liuice :
  auteurs mentionnés dans le thème Kvantum fourni.
- [Hyprland](https://github.com/hyprwm/Hyprland), [Waybar](https://github.com/Alexays/Waybar),
  [Rofi](https://github.com/davatorium/rofi), [awww](https://codeberg.org/LGFae/awww),
  [Alacritty](https://github.com/alacritty/alacritty), [Dolphin](https://invent.kde.org/system/dolphin).

Ce projet est une adaptation et une intégration de ces travaux. Les références
et limites de provenance figurent dans [CREDITS.md](CREDITS.md) et
[docs/AUDIT.md](docs/AUDIT.md).
