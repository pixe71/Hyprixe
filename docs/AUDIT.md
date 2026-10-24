# Audit technique

## Périmètre et méthode

Base : commit `f96dfb4`, dépôt initial sans modification locale. **593 fichiers**
inventoriés, 588 fichiers texte décodés entièrement ; les assets binaires ont
été identifiés et hachés. Le chiffre annoncé au premier point d’avancement était
une estimation, remplacée ici par le décompte exact de l’inventaire.

L’inventaire original contient pour chaque fichier son chemin, sa taille et son
SHA256 : [inventory-original.tsv](inventory-original.tsv). Les rôles des scripts,
leurs dépendances et leur rattachement aux entrées startup/keybinds ont été
examinés avant réorganisation. La revue a distingué les fonctions installées,
les exemples génériques KoolDots et l’état généré de la VM.

## Constats corrigés

| Constat initial | Traitement |
| --- | --- |
| Forçage global `LIBGL_ALWAYS_SOFTWARE` en double | Retiré de l’arbre natif ; profil explicite séparé |
| Hyprlock lancé avec trois overrides Mesa | Lanceur normal natif ; environnement optionnel fourni par le profil |
| Plusieurs règles moniteur génériques contradictoires, puis `Virtual-1` | Une règle wildcard, mode préféré, échelle/position automatiques |
| Workspace 1 lié à l’écran de la VM | Aucun workspace lié à un connecteur |
| Deux systèmes wallpaper et délai de 3 s | Un seul script, verrou flock, attente bornée de l’IPC/sorties |
| Daemon awww tué puis relancé | Réutilisation du daemon ; démarrage s’il manque, aucune destruction |
| Wallpaper dupliqué et caches par écran versionnés | Une image source ; Hyprlock utilise directement l’image installée |
| Fichiers config/style Waybar contenant simplement un chemin `/home/luc/...` | Vrais fichiers JSON/CSS avec imports résolus et rendus à l’installation |
| Superposition de raccourcis KoolDots, ALT et deux actions ALT+Tab | Une seule table native, contrôlée pour les doublons |
| SUPER+Tab en doublon groupe/workspace | Suppression de l’ambiguïté ; PageUp/PageDown pour les workspaces |
| Qt Widgets testé comme un module QML, repli Fusion injustifié | Kvantum pour Widgets, Basic pour Qt Quick, plugin Qt6 vérifié |
| Variables NVIDIA imposées à tous les GPU et curseur logiciel | Aucun pilote forcé dans native ; curseur logiciel réservé au profil VM |
| Autostarts Quickshell/overview/Kitty sans fichiers associés | Retirés du démarrage actif, exemples facultatifs conservés séparément |
| Palette Tokyo Night dans Alacritty | Harmonisation avec les couleurs bleu/cyan Frosted Glass ; opacité/padding conservés |
| CSS Waybar dupliqué, bouton power défini deux fois dont en rose | Une seule feuille Frosted-Glass, couleurs communes pour le bouton power |
| Liste packages issue de la VM | Dépendances actives, backports, options et guest integration séparés |

## Fonctionnalités conservées

Wallpaper, Kvantum et toolbar Dolphin d’origine sont vérifiés par SHA256.
Les valeurs de décoration sont inchangées : arrondi 13, opacité active 0.78 /
inactive 0.72, blur taille 4 / 3 passes, gaps 4/10, bordures 2 px et mêmes
couleurs. Rofi garde sa disposition KoolDots/adi1090x et sa palette translucide.
Waybar garde les couleurs/background et position haute ; MPRIS, tray et
inhibiteur d’inactivité sont également conservés.

Les applications actives sont Alacritty/Dolphin ; les fonctions audio, média,
luminosité, captures, notifications, presse-papiers, gestuelle et gestion des
fenêtres/workspaces restent accessibles. Alt+F10 reste un sélecteur graphique.
La navigation principale Alt+Tab utilise le dispatcher Lua officiel, sans
workaround destiné aux plantages Wayland de la VM.

Les thèmes alternatifs, météo/musique, quick settings, réparations de versions,
scripts SSH, outils SDDM/docks/Quickshell et réglages d’autres distributions sont
identifiés comme bibliothèque facultative dans `extras/kooldots`. Ils ne font
pas partie du déploiement. Leur syntaxe est contrôlée ; leurs références
externes ne constituent pas une promesse de fonctionnement dans Hyprixe.

## Retraits justifiés

- Ancienne sauvegarde `backup-before-tokyonight`, marqueurs de premier boot et
  fichiers de cache wallpaper : état généré, non nécessaire à une installation.
- Trois copies du wallpaper et version modifiée générée : l’original unique
  reste dans `wallpapers/min_forest.jpg`.
- Ancien script `SetFrostedWallpaper.sh` : remplacé par `Wallpaper.sh`, avec
  détection des sorties et sans variables graphiques natives.
- Thèmes Kitty et lanceur Thunar dédié : applications remplacées ; les scripts
  génériques de sélection upstream restent des références facultatives.
- Binaire précompilé `dots-tui-ubuntu-2404` (~17,7 Mo) : outil d’une autre
  distribution, non lancé par la configuration cible, sans source intégrée.
- Anciens noms Senshi-Tokyo-Night : remplacés par Frosted-Glass.

Les éventuelles occurrences Kitty/Thunar/Tokyo restantes sont confinées aux
exemples génériques et aux documents d’audit. Aucun défaut, raccourci, script ou
installateur actif ne lance ces applications. Les exemples d’écrans de la VM
sont conservés uniquement sous `profiles/vmware/monitor-examples` et ne sont
jamais appliqués automatiquement.

## Sécurité et limites

Aucun motif de token GitHub/AWS ou de clé privée n’a été trouvé dans les fichiers
actuels ni dans le seul commit de l’historique. Les noms de fichiers ont aussi été contrôlés pour `.env`, credentials,
cookies, historique shell, logs et caches. Les caches de la VM ont été retirés,
les ignorances complétées, et les copies temporaires/tests sont exclues du suivi.
Les tests ne déclenchent ni verrouillage, ni suspension, ni arrêt de machine.

L’installateur refuse root pour le déploiement, limite les cibles au HOME, refuse
les parents symboliques, sauvegarde par fichier, protège les sauvegardes et
vérifie leurs empreintes. Les appels réseau/build upstream utilisent des
révisions fixes et s’exécutent sans privilèges ; APT utilise les dépôts signés.
Les outils système facultatifs archivés ne sont jamais lancés.

La provenance exacte de Senshi/wallpaper reste à compléter : voir CREDITS.md.
Les tests sous WSL ne prouvent pas le rendu, les périphériques d’un PC, le
déverrouillage PAM ou la reprise après veille. Ces points sont explicitement
SKIPPED et nécessitent la procédure INSTALL.md sur la machine cible.
