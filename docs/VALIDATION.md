# Validation effectuée

Audit du 25 octobre 2026 (Europe/Paris), depuis Windows avec Debian 13 sous WSL2,
x86_64. **Aucune session Hyprland sur matériel physique n’a été démarrée.**
Les commandes graphiques interactives ne sont pas présentées comme testées.

## Commandes et résultats

Les contrôles ci-dessous ont réellement été exécutés sur les fichiers du dépôt.
Les préfixes absolus du répertoire de travail sont omis dans les commandes Linux.

| Commande / contrôle | Résultat constaté |
| --- | --- |
| `bash -n` sur tous les `*.sh`, via `verify.sh` | 131 scripts, aucune erreur, bibliothèque facultative incluse |
| `shellcheck -S error` sur tous les scripts | Aucune erreur de cette sévérité |
| `shellcheck -S warning` sur les scripts actifs | Aucun warning ni erreur |
| `luac -p` sur tous les `*.lua` | 82 fichiers, aucune erreur de syntaxe |
| `lua tests/check_lua.lua "$REPO/.config"`, avec XDG_CONFIG_HOME pointant sur cette config | Chargement complet, 64 combinaisons uniques, 13 raccourcis obligatoires présents, cycles avant/arrière et callbacks startup/hotplug exécutés contre une API mock explicite |
| `python3 -m unittest discover -s tests -v` | 32 tests, résultat OK dans le banc Debian WSL après le contrôle 0.56.2 ; détail ci-dessous |
| `./verify.sh`, avec les binaires compilés dans PATH | Zéro contrôle en échec ; les contrôles nécessitant la session réelle sont SKIPPED |
| `apt-get -s install` avec `packages.txt` | Résolution des 41 paquets réussie, code 0 |
| `apt-get -s install -t trixie-backports` avec `packages-backports.txt` | Résolution des 5 paquets réussie, code 0 |
| `apt-get -s install` avec `profiles/vmware/packages.txt` | Résolution des 2 paquets réussie, code 0 |
| `python3 scripts/check-deps.py` dans le banc sans bureau Hyprland | Code 1 attendu, liste explicite des commandes et du plugin Qt6 manquants, aucun déploiement |
| `bash scripts/build-runtime.sh STAGING_DIRECTORY` | awww + awww-daemon 0.12.1 compilés ; Rofi au commit 0b6aa8b (tag 2.0.0) compilé avec Wayland activé et XCB désactivé |
| Même script, binaires compilés déjà dans PATH | Code 0, aucun nouveau build/APT déclenché |
| `awww --version`, `awww-daemon --version`, `rofi -version` | `awww 0.12.1`, `awww-daemon 0.12.1`, `Version: 0b6aa8b` |
| `rofi -info`, affichage volontairement inexistant | `wayland enabled`, `xcb disabled` ; aucune fenêtre ouverte |
| `rofi -config FICHIER -dump-theme` | Les 6 fichiers Rasi actifs sont acceptés, code 0 ; cette voie utilise le vrai parseur avant création d’une fenêtre |
| Parseurs Python JSON/TOML/XML | Waybar, Alacritty, SVG Kvantum et XML Dolphin acceptés |
| Comparaison SHA256 des assets avec l’inventaire original | Wallpaper, deux fichiers Kvantum et toolbar Dolphin identiques |
| Scan des motifs VMware/logiciel, anciens défauts et chemins personnels dans `.config`, `.local`, `profiles/native` | Aucune correspondance |
| Scan de motifs de secrets dans les fichiers actuels et le seul commit historique | Aucun token GitHub/AWS ni clé privée correspondant aux motifs recherchés |
| Recherche du marqueur EXIF dans le wallpaper | Absent |
| Vérification des liens et des permissions Git | Aucun lien cassé ; entrypoints et scripts actifs enregistrés en mode 100755 |
| `git status --short`, `git diff HEAD`, `git diff --cached`, `git diff --check`, `git diff --cached --check` | Modifications revues, absence d’erreur de whitespace ; aucun commit créé |

Les résultats détaillés des fichiers sont consignés dans
[CHANGES.md](CHANGES.md). Les sources compilées, journaux de compilation,
fixtures et caches de test sont hors des fichiers livrés ; `.validation/` et
`__pycache__/` sont ignorés.

## Scénarios automatisés

Les tests utilisent des HOME temporaires distincts, supprimés ensuite. Ils
vérifient : installation native, deuxième installation sans nouvelle sauvegarde,
profil VMware puis retour au natif et restauration inverse ; sauvegarde d’une
ancienne entrée Lua/Hyprlang, conservation des fichiers personnels supplémentaires,
permissions originales, liens symboliques de fichiers, rejet de parents
symboliques, fusion MIME/KDE/Qt, chemins XDG personnalisés et espaces ; aperçu
sans copie, profil invalide, cible XDG hors HOME, sauvegarde corrompue, refus des
éditions post-installation et rollback après une erreur d’écriture injectée.

Le test des seuls bits de permission couvre un contenu inchangé avec mode
modifié. Les exécutables construits suivent également la sauvegarde/restauration.

Les mocks de commandes contrôlent : awww existant réutilisé, daemon manquant
démarré une seule fois, sorties DP/eDP dynamiques, application à tous les écrans,
échec borné sans relances répétées ; sélecteur Rofi sur un instantané unique,
annulation et index invalide ; démarrage Waybar par service activé ou lancement
direct avec les chemins config/CSS explicites. Un contrôle exécute aussi le vrai
`install.sh --dry-run` sous UID non privilégié via `setpriv`.

Ces tests valident la logique des scripts et des actions enregistrées. Les mocks
ne valident ni les dispatchers à l’intérieur d’un compositor, ni le rendu GPU.

## Échecs rencontrés et corrigés

- Une réinstallation déplaçait des lignes vides dans les fichiers INI fusionnés
  et créait une nouvelle transaction. Correction de la fusion, test d’idempotence
  vert sur le contenu final.
- Le premier build awww a révélé une dépendance de compilation manquante,
  `wayland-protocols`. Ajoutée, puis build complet réussi.
- ShellCheck a signalé une affectation vide ambiguë `DISPLAY=` dans la sonde
  Rofi. Remplacée par `DISPLAY=''`, contrôles actifs sans warning.
- `rofi -rasi-validate` segfaulte dans le build upstream 2.0.0 testé, y compris
  sur les fichiers de palette. La validation finale utilise `-config …
  -dump-theme`, voie initialisée du même parseur ; les six fichiers passent.
  Ce défaut d’outil de validation est documenté, sans conclure à un test visuel
  ou cacher un échec de la configuration normale.

## Contrôles restant SKIPPED ici

- `hyprctl configerrors` : Hyprland et son IPC de session ne sont pas disponibles
  dans le banc de validation ; syntaxe Lua et tests de chargement seulement.
- Installation complète de tous les paquets du bureau : APT a été simulé ; les
  dépendances C/Rust nécessaires aux builds ont réellement été installées dans
  Debian WSL. Aucun bureau complet ni gestionnaire de connexion installé pour
  prétendre à un test d’intégration graphique.
- Résultat visuel Frosted Glass : assets et paramètres vérifiés, aucune capture
  d’une session physique comparée.
- Raccourcis/clavier/souris, vrai cycle de focus, multi-écran/HiDPI/hotplug.
- Hyprlock/PAM, verrouillage avant veille et déverrouillage après reprise.
- Modules Waybar sur de vrais périphériques réseau, Bluetooth et audio ; GPU
  Intel/AMD/NVIDIA, accélération et profil VMware dans un vrai invité.
- Affichage du panneau d’information Dolphin au premier lancement sans état KDE
  préalable ; F11 et les étapes de contrôle sont documentés dans INSTALL.md.

Exécuter sur le PC cible :

```bash
./verify.sh --dependencies --session
hyprctl configerrors
hyprctl monitors -j
hyprctl binds -j
awww query
```

Puis tester SUPER+Return/E/Space/Q/L, les deux clics et les flèches, Alt+Tab dans
les deux sens, le rendu Dolphin/Kvantum, la veille/reprise et un branchement
d’écran. Les limites de provenance des assets Senshi sont décrites dans CREDITS.md.

## Complément : compatibilité Hyprland 0.56.2

Version fonctionnelle précisée par l’utilisateur : **0.56.2**. Audit des sources
au tag `v0.56.2`, commit `efb50993780079460b0cbed1363e2166a2de1d9f`.
**0.55.2 désigne le seuil minimal de l’installateur ; 0.56.2 est acceptée et
devient la référence documentée.** Ce seuil ne garantit pas toutes les versions
futures. Aucun paramètre visuel ni raccourci Lua n’a été modifié par ce contrôle.

| Élément | Vérification spécifique |
| --- | --- |
| Syntaxe et options Lua | Chargement complet avec le banc existant ; 49 noms d’options configurés comparés au registre `ConfigValues.cpp` 0.56.2, types bool/int/float acceptés |
| API | 25 noms de fonctions `hl.*` / dispatchers utilisés retrouvés dans les registrations du tag 0.56.2 |
| Souris | `mouse:272` + `window.drag()` et `mouse:273` + `window.resize()`, avec `{ mouse = true }`, correspondent exactement à l’exemple officiel 0.56.2 |
| Alt+Tab | `cycle_next({ next = true/false })` et `alter_zorder({ mode = "top" })` acceptés par les factories du tag ; les deux callbacks restent couverts par le test Lua |
| Window/layer rules | Propriétés class/title, float/center/pin, namespace/blur/ignore_alpha présentes dans les descripteurs 0.56.2 |
| Blur/décoration/animations | Options présentes dans le registre ; les 10 feuilles d’animation utilisées existent dans l’arbre du tag |
| Hyprlock | Protocole ext-session-lock-v1 toujours annoncé ; les 34 couples catégorie/champ utilisés existent dans le parseur Hyprlock 0.9.6. Ce fichier relève de Hyprlock, pas de la syntaxe Lua du compositor |
| Démarrage | Événements `hyprland.start` et `monitor.added` présents ; `hl.exec_cmd` conservé ; les commandes Hypridle/lock/menu utilisent les dispatchers Lua acceptés |
| Waybar | Incompatibilité des clics workspace de Waybar Debian 0.12 détectée et corrigée, voir ci-dessous |

### Correction Waybar strictement nécessaire

Dans ce tag Hyprland, la requête IPC `dispatch …` évalue
`hl.dispatch(…)`. Waybar Debian 0.12 envoie encore `dispatch workspace 1`, qui ne
constitue pas une expression Lua valide. Le défaut concerne les clics sur les
workspaces ; les modules de lecture JSON et le thème ne nécessitent pas de refonte.

Le build optionnel préparé par l’installateur conserve Waybar 0.12 et convertit
seulement les requêtes workspace vers `hl.dsp.focus` / `toggle_special`. Il
s’identifie `hyprixe-lua-ipc1`. Un Waybar upstream disposant déjà des deux chemins
IPC Lua est réutilisé, sans compilation. Le drop-in systemd pointe vers le binaire
sélectionné, y compris lorsqu’il est dans `~/.local/bin` ; sauvegarde/restauration
du binaire sont couvertes par les tests. Aucun CSS ou agencement Waybar modifié.

Six tests supplémentaires couvrent la détection des capacités et compilent le
petit adaptateur C++ pour soumettre ses résultats à un véritable interpréteur
Lua : workspace numérique, noms avec guillemets/antislash/retour à la ligne,
workspace sur moniteur courant, workspaces spéciaux et requêtes de lecture
inchangées. Les 32 tests passent. La compilation complète Waybar et son contrôle
de capacités sont réalisés dans Debian WSL, sans ouverture d’une session.

La comparaison au code source et les tests instrumentés ne remplacent pas
`hyprctl configerrors` dans une session 0.56.2, ni le test physique du glisser,
du resize, du cycle de focus et du verrouillage. Ces validations restent SKIPPED ici.

Sources primaires du contrôle :
[exemple officiel 0.56.2](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua),
[bindings/dispatchers](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsDispatchers.cpp),
[registre d’options](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/values/ConfigValues.cpp),
[traitement IPC](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/debug/HyprCtl.cpp),
[clics Waybar 0.12](https://github.com/Alexays/Waybar/blob/0.12.0/src/modules/hyprland/workspace.cpp),
[backend Lua Waybar upstream](https://github.com/Alexays/Waybar/blob/master/src/modules/hyprland/backend.cpp),
[parseur Hyprlock 0.9.6](https://github.com/hyprwm/hyprlock/blob/v0.9.6/src/config/ConfigManager.cpp).
