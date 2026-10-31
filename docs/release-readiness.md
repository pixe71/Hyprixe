# v1.0.0 release readiness

[Documentation index](README.md)

This is the dated pre-v1 audit. For the Core + Profiles branch, use the
[refactor validation record](core-profiles-validation.md). Historical findings
below are retained; this architecture work does not resolve artwork rights.

**Not ready for v1.0.0** — review dated **2026-10-30**.

Target: **Debian 13 Trixie**, native hardware, SDDM **Hyprland (uwsm-managed)**.
No commit, tag, release or Wiki publication was created by this preparation.
NixOS remains future work, not a supported v1 platform.

## Exact remaining blockers

| ID | Remaining requirement | How to close it |
| --- | --- | --- |
| A1 | Owner-reported Pinterest discovery is recorded in the asset audit, but original author/redistribution rights for `common/wallpapers/min_forest.jpg` remain unknown, including its SDDM/menu copies and screenshots | Record a reliable artwork license/permission, author and source, or deliberately replace it with cleared artwork and validate the result |
| S1 | `screenshot1.png` contains account/hostname/IP information and remains locally present | Replace it with a clean capture or intentionally omit it from the public commit/release; it is no longer embedded in the README |
| P1 | This candidate has no completed physical Debian acceptance record | Run the commands/manual checklist below, including repeat installation and safe restore, and record exact versions/results |

Details: [asset evidence/licenses](assets-provenance.md) and
[screenshot review/six final capture slots](screenshots/README.md).
Captures 2/3 pass visible personal-data review but remain subject to A1.
No artwork rights were inferred from a collector's repository license.

**A2 is closed: Kvantum cleared for v1.0.0.** The original pair is a proven
Graphite light derivative under GPLv3, with source, credits and its exact GPL
notice retained. The compatible Senshi MIT notice remains alongside it.
See [file-by-file evidence](assets-provenance.md#kvantum-file-by-file-findings).
This does not change A1, S1 or P1, nor the overall release verdict.

## Technical inconsistencies resolved

- [x] Installer preflight and live verifier share
  [one Hyprland policy](hyprland-compatibility.md): minimum 0.55.2, reference
  release numbers 0.55.2 and 0.56.2, provisional warnings for other eligible
  versions, no speculative upper bound.
- [x] Actual API/configuration errors still fail. Tests cover future working
  and broken APIs, old/malformed/failed queries, reference/packaged/prerelease
  outputs, and installer/live consistency.
- [x] `profiles/debian/packages/packages-optional.txt` uses **qalc**, Debian's optional package
  [providing `/usr/bin/qalc`](https://packages.debian.org/trixie/amd64/qalc/filelist).
  No new default application or keybinding was added.
- [x] Identified a matching pinned Senshi distribution copy: wallpaper byte match,
  Kvantum text match after line-ending normalization. Historical statements
  that its URL was entirely unknown are superseded by the new asset evidence.
- [x] Matched all four archived Catppuccin files to an exact upstream revision;
  retained its MIT notice, together with Senshi and Nerd Fonts notices.
- [x] Corrected gitstatus attribution: separate **GNU GPLv3**, already retained
  by the installer. Powerlevel10k itself remains MIT.
- [x] Closed the Kvantum license chain with pinned Graphite/Senshi comparisons:
  710/710 SVG shapes, 174/174 paths, 1,139 retained IDs; 456 unchanged config
  values. Original files remain unchanged; Graphite GPLv3 and required notices
  are recorded in the asset audit/inventory.

No compositor setting, layout, keybinding, menu behaviour, service ordering,
profile, wallpaper, image or font was changed by these fixes.

## Automated validation in the editor environment

The editor runs on Windows with **Debian 13 WSL**, without a deployed Hyprixe
desktop/user session. Prepared native Rofi/Waybar/awww binaries and a verified
shell-assets fixture support the regression tests. Logs stay outside Git at
`/root/.cache/hyprixe-validation/release-v1-*.log`.

| Command/check | Actual result |
| --- | --- |
| Focused `python3 -m unittest test_hyprland_version test_keybind_checks -v`, with scripts/tests on PYTHONPATH | 25 tests passed |
| `./verify.sh` | Exit 0; 245 tests passed; `RESULT: 0 failed check(s)` |
| `umask 0002; ./verify.sh` | Exit 0; 245 tests passed; `RESULT: 0 failed check(s)` |
| `./verify.sh --dependencies` | 245 tests passed; 13 installed-environment failures in undeployed WSL |
| `./verify.sh --dependencies --session` | 245 tests passed; 17 environment/session failures without a graphical session |
| Real `Hyprland --verify-config` through the isolated parser helper as UID 65534 | Passed on 0.55.2: private config, 68 handles, dispatcher constructors; no graphical session started |
| Debian APT metadata and official file list | qalc available in Trixie and provides the command; no qalculate candidate |
| Asset comparisons | Exact wallpaper, normalized Senshi theme and historical Catppuccin matches; no asset modifications |
| Screenshot review | Three viewed; no PNG text/EXIF metadata; capture 1 fails privacy |

Source validation includes Bash syntax/ShellCheck, Lua syntax/mock load,
Python parsing, native Kitty/Rasi/GTK CSS/QML checks, imports, original hashes,
service ordering and isolated deployment/restore regressions. Interactive
probes remain SKIPPED. The separate unprivileged parser run closes the main
root account's parser SKIP; it does not prove physical rendering.

Dependency/session failures reflect absent installed files/tools, undeployed
Qt/font/menu configuration, the editor account's Bash shell and missing live
Hyprland/UWSM environment. They are not classified as Hyprixe bugs or hidden.
Final link/whitespace/asset-integrity counts are recorded below. Earlier test
evidence retains its dated context in [VALIDATION.md](VALIDATION.md).

### Final repository checks

- Markdown links, images, exact filename case and heading anchors: 39 Markdown
  files, 211 relative targets and 44 canonical repository/Wiki links; zero failures.
- Markdown structure/whitespace: 37 maintained pages, zero failures.
- Earlier external reachability pass: 74 of 75 tested URLs returned HTTP 200. The official Hyprland
  UWSM page returned HTTP 400 to the direct WSL probe; it was accessible through
  the web tool during the documentation review. No remote-anchor validation
  or guarantee about future network availability is claimed.
- The owner-provided Pinterest reference could not be retrieved by the web tool, so its contents
  are not independently verified. Author/license remain unknown and A1 stays
  open. The wallpaper SHA256 remains unchanged; this update is documentation-only.
- `git diff --check` and `git diff --cached --check`: passed.
- All 18 inventoried image/font/Kvantum-config assets retain their audit-start
  SHA256; no screenshot or theme asset edited. Required third-party notices
  and the intentional inventory are the only new asset-documentation files.
- Source/runtime files changed only for the shared version policy, optional
  qalc package entry and regression tests; no desktop configuration changed.
- Existing case-only ROFI/WAYBAR/WLOGOUT guide renames remain staged from the
  documentation pass. No additional staging, commit, tag or release occurred.

### Kvantum closure validation

The file-specific GPL review on 2026-10-30 adds pinned Graphite/Senshi source
references and one exact GPL notice; the external-URL catalog now has 81 entries.
The earlier reachability totals above are a dated pass, not a claim that every
new link was part of it. The relevant pinned source files/license were fetched
and hashed directly from upstream.

After the documentation/license updates, `./verify.sh` passed all **245 tests**
and ended with `RESULT: 0 failed check(s)`. `git diff --check` and
`git diff --cached --check` passed. All 18 asset hashes, every pre-existing
non-documentation file and the Git index were unchanged by this closure task.
The five changed files are CREDITS, the README's remaining-rights wording,
the asset audit, its JSON inventory and this readiness record; the only new
file is `docs/licenses/Graphite-GPL-3.0.txt`. Logs/research stay outside Git at
`/root/.cache/hyprixe-validation/kvantum-provenance*`.

## Physical Debian acceptance checklist

Record date, Debian/Hyprland/Waybar/Rofi/Kitty/Zsh versions, GPU/driver and
scaling locally. Do not publish personal identifiers or IPs with evidence.
Save work and close Dolphin before full deployment. Run as the normal
sudo-enabled desktop user, never `sudo ./install.sh`.

### 1. Install and verify

```bash
cd ~/hyprixe-debian
git status --short
./install.sh native
./verify.sh
./verify.sh --dependencies
```

- [ ] Installation exits 0 without mismatched/downgraded build libraries.
- [ ] A dated backup covers changed user files, linked SDDM and any shell change.
- [ ] Both verifier commands end with `RESULT: 0 failed check(s)`.
- [ ] Review SKIPPED items and complete applicable manual checks.

### 2. Full reboot and UWSM login

Save work and reboot normally. Select **Hyprland (uwsm-managed)** in SDDM:

```bash
hyprctl version
hyprctl configerrors
uwsm check is-active -v compositor-only
systemctl --user is-active graphical-session.target hyprixe-session.target
systemctl --user status waybar.service hyprixe-awww.service hyprixe-wallpaper.service --no-pager
./verify.sh --dependencies --session
```

- [ ] SDDM password/session chooser works; no forced virtual keyboard.
- [ ] No unexplained white/blank transition; wallpaper appears and stays.
- [ ] `configerrors` is empty, targets active, Waybar/awww running; wallpaper
  oneshot normally `active (exited)`.
- [ ] Session verification reaches zero failures. Record provisional-version
  warnings without claiming a previously validated release.

### 3. Desktop, applications and input

- [ ] **Waybar:** rounded corners, tray, metrics, adaptive temperature/storage,
  taskbar focus/active icons, clock/calendar and power button.
- [ ] **Rofi:** `SUPER + Space`, immediate typing, sidebar actions, mouse/keys,
  Enter/Escape and readable wallpaper/blur.
- [ ] **Clipboard:** text/image history, `SUPER + CTRL + V`, copy, cancel and delete.
- [ ] **Switcher:** Alt+F10 focuses the exact window; cancel has no effect;
  Alt+Tab and reverse cycle the current workspace.
- [ ] **Wlogout:** both shortcuts toggle one menu, four actions only, keyboard
  navigation works, Cancel prevents logout/reboot/shutdown.
- [ ] **Kitty/Zsh/P10k:** `SUPER + Return`, `zsh --version`, `echo "$SHELL"`,
  `ps -p $$ -o comm=`; Git clean/dirty/untracked, glyphs, suggestions,
  highlighting and quiet prompt startup.
- [ ] **Dolphin/Kvantum:** accepted interface preserved; light glass, readable
  text/selection/context menus, preview and blur.
- [ ] **Lock:** `SUPER + L` and actual password/PAM unlock succeed.
- [ ] **Screenshots:** area copy, full/area save, unique names, directory
  creation, image paste and cancelled area selection.
- [ ] **Workspaces/input:** 1–4 persistent after login/reload, switching/moving
  windows, mouse move/resize and focus/move/resize arrows.
- [ ] **Network:** reconnect and NetworkManager click/tooltip behaviour.
- [ ] **Bluetooth:** adapter/device/menu if present; record N/A if absent.
- [ ] **Audio:** output, mute, scroll, media keys and microphone mute.
- [ ] **Battery/brightness:** percentage/charge/low states where hardware
  exists; absent battery hides; record genuine N/A instead of a fake pass.
- [ ] **Idle/resume:** eye inhibits automatic idle, lock/DPMS and actual
  suspend/resume restore the desktop. No automatic suspend timer or Wlogout
  Suspend/Hibernate button is expected.
- [ ] **Notifications/Polkit:** notification delivery and authentication prompts.
- [ ] **Outputs:** applicable hotplug/scaling changes retain wallpaper/taskbar
  behaviour without fixed connector names.

### 4. Reinstallation and safe restore

Use the same checkout/profile, close Dolphin and keep backup IDs/logs:

```bash
./uninstall.sh --list
./install.sh native
./verify.sh
./verify.sh --dependencies --session
./uninstall.sh --list
```

- [ ] Repeat installation succeeds without duplicate bindings/daemons/themes.
- [ ] Same inputs leave managed-file payloads unchanged and create no
  unnecessary backup transaction. APT upgrades are separate from file idempotence.
- [ ] Optionally repeat `./install.sh native --no-packages` after the normal
  run to check prepared offline assets without new APT/build work.
- [ ] In a **safe test account**, preview and restore the matching transaction
  using `--backup=BACKUP_ID --dry-run` then `--backup=BACKUP_ID`. Verify old
  file contents/modes, shell and linked SDDM state. Follow
  [restore](uninstall-restore.md); do not experiment on unsaved working sessions.

### 5. Session exit and power

Test separately after saving work; reconnect between tests:

- [ ] Confirmed **Logout** returns cleanly to SDDM through UWSM; log in again.
- [ ] Confirmed **Reboot** returns to usable SDDM/UWSM.
- [ ] Confirmed **Shutdown** powers off; boot and log in again.
- [ ] Final `./verify.sh --dependencies --session` still returns zero failures.

## Release decision

- [x] Close A2 with Graphite-derived GPLv3 evidence and retained notices.
- [ ] Close A1 with artwork rights evidence, not a guessed license label.
- [ ] Close S1 and approve the [six final capture slots](screenshots/README.md).
- [ ] Close P1 with exact commands, exit statuses and manual observations.
- [ ] Review README/docs/Wiki links and the complete Git diff/state.
- [ ] Deliberately select public files and required notices; omit private
  capture 1, caches, test logs and downloaded research.
- [ ] Only then explicitly decide to commit/tag/publish; none is automatic.

Change the verdict to **Ready for v1.0.0** only after those conditions are met.
Current verdict remains **Not ready for v1.0.0**.
