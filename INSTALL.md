# Installer Hyprixe Debian

## Prérequis

- Debian GNU/Linux **13 (trixie)**, compte utilisateur normal, accès à `sudo`,
  connexion réseau et plusieurs Go libres pour APT et les premières compilations.
- Pilotes DRM/Mesa ou NVIDIA adaptés au matériel, session logind/DBus utilisable.
  Le dépôt n’installe pas automatiquement de pilote propriétaire.
- Un gestionnaire de connexion déjà installé, ou une console locale permettant
  de démarrer Hyprland. Le script ne remplace pas votre gestionnaire de connexion.
- Hyprland **0.56.2** est la version de référence de cette configuration Lua et
  la version fonctionnelle indiquée par l’utilisateur. Ses API et options ont été
  vérifiées au tag upstream v0.56.2. **0.55.2 reste le seuil minimal accepté** par
  l’installateur : la mention 0.55.2+ n’impose aucune rétrogradation vers 0.55.2.
  Les métadonnées trixie-backports consultées proposent `0.55.2+ds-1~bpo13+1` ;
  conserver votre installation fonctionnelle de 0.56.2. Le script ne fixe pas de
  version APT exacte. Une version antérieure au seuil est refusée avant copie.

Si `sudo`/`git` manquent, les installer depuis un compte administrateur puis
revenir au compte qui ouvrira la session graphique :

```bash
su -
apt update
apt install sudo git
usermod -aG sudo VOTRE_COMPTE
exit
# Se déconnecter/reconnecter pour activer le groupe sudo.
```

## Installation

Fermer Dolphin, Alacritty et les éditeurs de configuration pour éviter qu’ils
réécrivent leurs préférences pendant la copie.

```bash
git clone https://github.com/pixe71/hyprixe-debian.git
cd hyprixe-debian
./install.sh
```

Équivalents et options :

```bash
./install.sh native
./install.sh vmware
./install.sh --dry-run
./install.sh native --no-packages
```

Ne pas lancer `sudo ./install.sh`. Le déploiement s’effectue avec votre compte ;
seules les commandes APT utilisent `sudo`. Sur une copie ayant perdu les bits
exécutables, utiliser `chmod +x install.sh uninstall.sh verify.sh scripts/build-runtime.sh`.

Le mode `--dry-run` affiche les chemins qui seraient modifiés, sans APT ni copie.
Il ne garantit pas que les dépendances sont déjà installées. `--no-packages`
contrôle les commandes, la version Hyprland, le backend Wayland de Rofi et le
plugin Qt6 Kvantum ; il échoue avant de toucher aux configurations si l’un manque.

## Dépendances et effets système

`packages.txt` contient les applications Debian stables réellement utilisées.
`packages-backports.txt` contient Hyprland, Hyprlock, Hypridle, XWayland et le
portail Hyprland. `packages-optional.txt` reste facultatif. Le profil VMware
installe également les paquets de `profiles/vmware/packages.txt`.

Si aucun dépôt trixie-backports n’est configuré, l’installateur crée uniquement
`/etc/apt/sources.list.d/hyprixe-backports.sources`, vers le dépôt Debian officiel
signé par la clé Debian. Un fichier existant à ce nom n’est pas écrasé. Les
paquets Hyprland sont demandés explicitement à trixie-backports.

Debian stable fournit Rofi 1.7.5 X11 dans les index utilisés lors de l’audit ;
awww n’y est pas empaqueté. Si nécessaire, `scripts/build-runtime.sh` construit :

| Programme | Source et révision fixe |
| --- | --- |
| Rofi 2.0.0, Wayland | `davatorium/rofi`, `0b6aa8ba8b4879f00c3cc96f2e47a13c079fe814` |
| awww 0.12.1 | `codeberg.org/LGFae/awww`, `f66e12a76dbc4c669b2f1375f78bce49f5b19d66` |
| Waybar 0.12, si son IPC Lua manque | `Alexays/Waybar`, `8490a1d9b9a5c8770dd63e9faca0a5e01acedcae`, adaptation locale limitée dans `scripts/waybar-lua-ipc.hpp` |

Le script vérifie les commits, initialise les sous-modules aux révisions
enregistrées et utilise `cargo build --release --locked`. Il installe les outils
C/Meson et Rust/Cargo des backports nécessaires à cette compilation. Les sources
sont compilées sans privilèges dans un répertoire temporaire supprimé ensuite.
Les exécutables préparés sont déployés dans `~/.local/bin` avec le même système de
sauvegarde que les configurations. Les versions déjà capables sont réutilisées.
Le support Waybar est détecté par la présence de ses commandes IPC Lua compilées,
sans envoyer d’action au compositor. Le Waybar stable 0.12 n’en dispose pas : sa
version préparée convertit uniquement les changements de workspace en
`hl.dsp.focus` / `hl.dsp.workspace.toggle_special`. Les requêtes JSON de lecture,
les modules et le CSS ne changent pas. Le correctif est identifié par
`hyprixe-lua-ipc1` dans `waybar --version`. Les headers C++/GTK nécessaires sont
installés par APT si cette compilation est requise.
Le PATH de Hyprland inclut ce répertoire. Pour les commandes de diagnostic depuis
une console existante, exécuter `export PATH="$HOME/.local/bin:$PATH"`.

Les téléchargements APT/Cargo/Git demandent un accès réseau. Si la compilation
échoue, les configurations utilisateur ne sont pas déployées ; les paquets APT
déjà installés restent présents. Aucune commande `curl | sh` n’est utilisée.

## Fichiers modifiés et sauvegardes

L’installateur copie les fichiers de `.config/`, la toolbar sous
`.local/share/kxmlgui5/dolphin/` et le wallpaper sous
`~/.local/share/hyprixe/wallpapers/min_forest.jpg`. Il ne copie jamais `extras/`.
Il sélectionne `profile.lua` et `profile.env` depuis le profil demandé.

Les valeurs concernées de `mimeapps.list`, `kdeglobals` et `qt6ct.conf` sont
fusionnées : les autres associations MIME, groupes et préférences sont conservés.
Le fichier spécifique `hyprland-mimeapps.list` reçoit aussi l’association des
dossiers pour éviter qu’un ancien choix propre à cette session soit prioritaire.
Dolphin devient l’application pour `inode/directory`. Alacritty est le terminal
de Hyprland, Rofi et KDE. Le thème Qt Widgets est Kvantum ; Qt Quick utilise Basic.
Un drop-in `systemd/user/waybar.service.d/hyprixe.conf` fournit le chemin du binaire
Waybar sélectionné et les mêmes chemins
au service Waybar s’il était déjà activé. Le script ne l’active pas globalement ;
il réutilise le service existant ou démarre directement une instance protégée
par flock. Ce drop-in est lui aussi sauvegardé et restauré.

Un ancien `hypr/hyprland.conf` est sauvegardé puis retiré pour qu’il ne prenne pas
le pas sur l’entrée Lua. Les fichiers personnels supplémentaires ne sont pas
supprimés. Les fichiers gérés présents sont sauvegardés **avant toute écriture**.

```text
~/.local/state/hyprixe/backups/DATE_UTC-PROFIL/
├── manifest.json     chemins, état avant/après, empreintes et permissions
├── files/            fichiers originaux, y compris les liens symboliques
└── complete          transaction terminée
```

Les sauvegardes sont privées (répertoire `0700`). Une erreur de copie déclenche
le retour arrière des écritures déjà effectuées. Une deuxième installation
identique ne recopie rien et ne crée pas de sauvegarde supplémentaire. Une
réinstallation après édition personnelle sauvegarde la version éditée.

Les variables XDG_CONFIG_HOME, XDG_DATA_HOME et XDG_STATE_HOME sont acceptées
si elles désignent des sous-répertoires absolus et réels du HOME. Les chemins
Hyprlock, Rofi, Hypridle et Waybar sont rendus en conséquence. Des parents
symboliques sont refusés pour éviter d’écrire à travers un autre gestionnaire
de dotfiles : sauvegarder/détacher d’abord ces liens et relancer.

## Restaurer / désinstaller

```bash
./uninstall.sh --list
./uninstall.sh --dry-run
./uninstall.sh
./uninstall.sh --backup ID_AFFICHE_PAR_LIST
```

Par défaut, la dernière transaction non restaurée est annulée. Les fichiers
précédents retrouvent leur contenu et leurs permissions ; les fichiers créés par
la transaction sont retirés. Seuls les répertoires créés devenus vides sont
retirés. Les autres fichiers personnels restent en place.

Si un fichier installé a été modifié depuis, la restauration refuse l’ensemble
de l’opération et affiche les chemins concernés. Copier vos éditions ailleurs,
remettre ces fichiers dans leur état installé puis relancer. Aucun `--force`
destructif n’est proposé. Les empreintes des sauvegardes sont vérifiées avant
restauration. Pour revenir à l’état antérieur à plusieurs installations, annuler
les transactions de la plus récente à la plus ancienne ; ne pas effacer les
sauvegardes intermédiaires. Une restauration interrompue peut être relancée.

Les paquets APT et le dépôt backports ne sont pas désinstallés automatiquement.
Ils peuvent servir à d’autres applications ; gérer leur retrait séparément avec
APT. Se reconnecter après restauration ou changement de profil.

## Premier lancement

Se déconnecter, choisir **Hyprland** dans le gestionnaire de connexion, se
reconnecter. Depuis une console locale sans gestionnaire, utiliser `Hyprland`
dans une session utilisateur logind. Ne pas lancer un deuxième compositor
depuis votre session graphique existante.

```bash
Hyprland --version
hyprctl version
hyprctl configerrors
hyprctl monitors -j
hyprctl binds -j
./verify.sh --dependencies --session
```

`configerrors` doit être vide. Les écrans doivent correspondre au matériel.
La règle par défaut utilise le mode et l’échelle préférés de chaque sortie.
Pour personnaliser une sortie, modifier `UserConfigs/monitors.lua` après avoir
consulté `hyprctl monitors`, puis `hyprctl reload`.

Les modules Lua sont chargés explicitement. Pour recharger après une édition :

```bash
hyprctl reload
hyprctl configerrors
```

Les changements d’environnement/profil et le passage Hyprlang → Lua nécessitent
une nouvelle session, même si le rechargement ne signale pas d’erreur.

## Contrôler les composants

```bash
# Waybar : démarrage s’il manque ; journal dans session.log.
~/.config/hypr/scripts/WaybarStartup.sh
# Recharger CSS/config d’une instance existante :
pkill -USR2 -x waybar

# Wallpaper : réutilise le daemon, détecte toutes les sorties.
~/.config/hypr/scripts/Wallpaper.sh
awww query

# Verrouillage interactif (à tester avec le mot de passe du compte).
~/.config/hypr/scripts/LockScreen.sh

# Applications
alacritty
dolphin
~/.config/hypr/scripts/RofiLauncher.sh
xdg-mime query default inode/directory
```

Si XDG_CONFIG_HOME est personnalisé, remplacer `~/.config` dans ces commandes
manuelles. Les scripts de session utilisent déjà les variables XDG.

Hyprlock lit la même image que awww, directement depuis le répertoire de données :
il ne dépend pas d’un cache généré pendant le démarrage. Tester le verrouillage
et le déverrouillage avant d’utiliser la veille. Hypridle verrouille après
10 minutes, puis éteint les sorties après 12 minutes. Pas de suspension
automatique ; l’inhibiteur Waybar peut suspendre l’inactivité.

Dolphin conserve la toolbar minimale, les réglages Places/InformationPanel et
les plugins d’aperçu. `F9` affiche Places, `F11` Information, `F12` les aperçus.
Sur un premier démarrage KDE sans état de fenêtre préalable, afficher le panneau
d’information avec F11 si nécessaire : aucun état binaire de géométrie de la VM
n’est distribué. Le panneau terminal intégré de Dolphin dépend de KonsolePart,
facultatif ; la commande « ouvrir un terminal » utilise Alacritty.

## Diagnostic et limites

- Journaux : `~/.local/state/hyprixe/session.log` et `wallpaper.log`.
- Aucun daemon awww n’est tué par les scripts actifs. L’attente de 5 s maximum
  concerne la disponibilité de son IPC et de ses sorties, pas un délai fixe de
  démarrage. Le hotplug relance seulement l’application de l’image.
- Éviter un second service Waybar/Hypridle ou un autre outil de wallpaper déjà
  activé dans une configuration personnelle. Le démarrage détecte les instances
  présentes ; il ne modifie pas leurs unités systemd.
- Le profil natif ne force aucun pilote NVIDIA/Intel/AMD. Installer le pilote
  approprié au GPU ; vérifier DRM et l’accélération avant d’attribuer un défaut
  de rendu au thème.
- Alt+Tab parcourt les fenêtres du workspace courant. Alt+F10 affiche toutes
  les fenêtres dans Rofi. Le cycle suit l’ordre Hyprland du workspace courant ;
  le sélecteur graphique se valide avec Entrée.
- La bibliothèque `extras/kooldots` contient des exemples génériques non portés
  intégralement à cet ensemble réduit. Ses outils de mise à jour, thèmes,
  repairs Fedora/Ubuntu et scripts SSH ne sont jamais lancés ni installés.
- `./verify.sh` affiche **SKIPPED** pour les contrôles graphiques indisponibles.
  Les validations réellement effectuées figurent dans [docs/VALIDATION.md](docs/VALIDATION.md).

Références primaires : [Hyprland Lua 0.56.2](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua),
[paquet Debian backports](https://packages.debian.org/source/trixie-backports/hyprland),
[instructions backports Debian](https://backports.debian.org/Instructions/),
[Qt/KDE Debian 13](https://wiki.debian.org/PkgQtKde/TrixieReleasePlans),
[Kvantum Qt6](https://packages.debian.org/trixie/qt6-style-kvantum),
[KXMLGUI6 conserve kxmlgui5](https://github.com/KDE/kxmlgui/blob/v6.13.0/src/kxmlguiclient.cpp),
[compilation Rofi](https://github.com/davatorium/rofi/blob/2.0.0/INSTALL.md).
