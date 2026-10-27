# Validation performed

Audit dated October 25, 2026 (Europe/Paris), from Windows with Debian 13 under
WSL2, x86_64. **No Hyprland session on physical hardware was started.**
Interactive desktop login is not presented as tested. The later SDDM section
records separate greeter test-mode rendering, not a physical login session.

## Commands and results

The checks below were actually run against the repository files.
Absolute working-directory prefixes are omitted from Linux commands.

| Command / check | Observed result |
| --- | --- |
| `bash -n` on all `*.sh` files, through `verify.sh` | 131 scripts, no errors, including the optional library |
| `shellcheck -S error` on all scripts | No findings at this severity |
| `shellcheck -S warning` on active scripts | No warnings or errors |
| `luac -p` on all `*.lua` files | 82 files, no syntax errors |
| `lua tests/check_lua.lua "$REPO/.config"`, with XDG_CONFIG_HOME pointing to this configuration | Full load, 64 unique combinations, 13 required bindings present, forward/backward cycling and startup/hotplug callbacks executed against an explicit mock API |
| `python3 -m unittest discover -s tests -v` | 32 tests, OK in the Debian WSL test environment after the 0.56.2 review; details below |
| `./verify.sh`, with compiled binaries in PATH | Zero failed checks; checks requiring a real session are SKIPPED |
| `apt-get -s install` with `packages.txt` | All 41 packages resolved successfully, exit code 0 |
| `apt-get -s install -t trixie-backports` with `packages-backports.txt` | All 5 packages resolved successfully, exit code 0 |
| `apt-get -s install` with `profiles/vmware/packages.txt` | Both packages resolved successfully, exit code 0 |
| `python3 scripts/check-deps.py` in the environment without a Hyprland desktop | Expected exit code 1, explicit list of missing commands and Qt6 plugin, no deployment |
| `bash scripts/build-runtime.sh STAGING_DIRECTORY` | awww + awww-daemon 0.12.1 built; Rofi at commit 0b6aa8b (tag 2.0.0) built with Wayland enabled and XCB disabled |
| Same script, with compiled binaries already in PATH | Exit code 0, no new build/APT operations triggered |
| `awww --version`, `awww-daemon --version`, `rofi -version` | `awww 0.12.1`, `awww-daemon 0.12.1`, `Version: 0b6aa8b` |
| `rofi -info`, with a deliberately nonexistent display | `wayland enabled`, `xcb disabled`; no window opened |
| `rofi -config FILE -dump-theme` | All 6 active Rasi files accepted, exit code 0; this path uses the real parser before creating a window |
| Python JSON/TOML/XML parsers | Waybar, Alacritty, Kvantum SVG and Dolphin XML accepted |
| Asset SHA256 comparison against the original inventory | Wallpaper, both Kvantum files and Dolphin toolbar identical |
| Scan for VMware/software-rendering patterns, old defaults and personal paths in `.config`, `.local`, `profiles/native` | No matches |
| Secret-pattern scan in current files and the single historical commit | No GitHub/AWS tokens or private keys matching the searched patterns |
| EXIF marker search in the wallpaper | Absent |
| Link and Git permission checks | No broken links; entry points and active scripts recorded as mode 100755 |
| `git status --short`, `git diff HEAD`, `git diff --cached`, `git diff --check`, `git diff --cached --check` | Changes reviewed, no whitespace errors; no commit created |

Detailed file changes are recorded in [CHANGES.md](CHANGES.md).
Compiled sources, build logs, fixtures and test caches are outside the delivered
files; `.validation/` and `__pycache__/` are ignored.

## Automated scenarios

Tests use separate temporary HOME directories, removed afterwards.
They check: native installation, a second installation without a new backup,
switching to VMware and back to native and restoring in reverse order;
backup of an old Lua/Hyprlang entry point, preservation of additional personal
files, original permissions, file symlinks, rejection of symlinked parent
directories, MIME/KDE/Qt merging, custom XDG paths and spaces; preview without
copying, invalid profile, XDG target outside HOME, corrupted backup, refusal
of post-installation edits and rollback after an injected write error.

The permission-only test covers unchanged contents with a changed mode.
Built executables are also covered by backup/restoration.

Command mocks check: reuse of an existing awww daemon, a missing daemon
started only once, dynamic DP/eDP outputs, application to all monitors,
bounded failure without repeated restarts; a Rofi switcher using a single
snapshot, cancellation and an invalid index; Waybar startup through an
enabled service or direct launch with explicit config/CSS paths.
One check also runs the real `install.sh --dry-run` under an unprivileged UID
through `setpriv`.

These tests validate script logic and recorded actions. Mocks do not validate
dispatchers inside a compositor or GPU rendering.

## Failures encountered and addressed

- Reinstallation moved blank lines in merged INI files and created a new
  transaction. The merge was corrected; the idempotence test passes on the
  final contents.
- The first awww build exposed a missing build dependency,
  `wayland-protocols`. It was added, then the full build succeeded.
- ShellCheck reported an ambiguous empty `DISPLAY=` assignment in the Rofi
  probe. It was replaced with `DISPLAY=''`; active checks report no warnings.
- `rofi -rasi-validate` segfaults in the tested upstream 2.0.0 build, including
  on palette files. Final validation uses `-config … -dump-theme`, an
  initialized path through the same parser; all six files pass.
  This validation-tool defect is documented without claiming a visual test
  or hiding a failure of the normal configuration.

## Checks still SKIPPED here

- `hyprctl configerrors`: Hyprland and its session IPC are unavailable in the
  validation environment; only Lua syntax and loading tests were performed.
- Full installation of all desktop packages: APT was simulated; C/Rust build
  dependencies were actually installed in Debian WSL. No complete desktop or
  display manager was installed to claim graphical integration testing.
- Frosted Glass appearance: assets and settings checked, no physical-session
  screenshot compared.
- Keybindings/keyboard/mouse, actual focus cycling, multi-monitor/HiDPI/hotplug.
- Hyprlock/PAM, locking before suspend and unlocking after resume.
- Waybar modules on real network, Bluetooth and audio devices; Intel/AMD/NVIDIA
  GPUs, acceleration and the VMware profile inside a real guest.
- Dolphin information-panel visibility on first launch without prior KDE
  state; F11 and verification steps are documented in INSTALL.md.

Run on the target PC:

```bash
./verify.sh --dependencies --session
hyprctl configerrors
hyprctl monitors -j
hyprctl binds -j
awww query
```

Then test SUPER+Return/E/Space/Q/L, both mouse clicks and arrow keys, Alt+Tab
in both directions, Dolphin/Kvantum rendering, suspend/resume and connecting
a monitor. Senshi asset provenance limitations are described in CREDITS.md.

## Addendum: Hyprland 0.56.2 compatibility

Working version specified by the user: **0.56.2**. Sources audited at tag
`v0.56.2`, commit `efb50993780079460b0cbed1363e2166a2de1d9f`.
**0.55.2 is the installer's minimum threshold; 0.56.2 is accepted and becomes
the documented reference version.** This threshold does not guarantee all
future versions. No visual settings or Lua keybindings were changed during
this review.

| Item | Specific check |
| --- | --- |
| Lua syntax and options | Full load with the existing test environment; 49 configured option names compared against the 0.56.2 `ConfigValues.cpp` registry, bool/int/float types accepted |
| API | 25 used `hl.*` function / dispatcher names found in the 0.56.2 tag's registrations |
| Mouse | `mouse:272` + `window.drag()` and `mouse:273` + `window.resize()`, with `{ mouse = true }`, exactly match the official 0.56.2 example |
| Alt+Tab | `cycle_next({ next = true/false })` and `alter_zorder({ mode = "top" })` accepted by the tag's factories; both callbacks remain covered by the Lua test |
| Window/layer rules | class/title, float/center/pin, namespace/blur/ignore_alpha properties present in the 0.56.2 descriptors |
| Blur/decoration/animations | Options present in the registry; all 10 animation leaves used exist in the tag's tree |
| Hyprlock | ext-session-lock-v1 protocol still advertised; all 34 category/field pairs used exist in the Hyprlock 0.9.6 parser. This file belongs to Hyprlock, not the compositor's Lua syntax |
| Startup | `hyprland.start` and `monitor.added` events present; `hl.exec_cmd` retained; Hypridle/lock/menu commands use accepted Lua dispatchers |
| Waybar | Workspace-click incompatibility in Debian Waybar 0.12 detected and fixed, see below |

### Required Waybar correction

In this Hyprland tag, the `dispatch …` IPC request evaluates
`hl.dispatch(…)`. Debian Waybar 0.12 still sends `dispatch workspace 1`,
which is not a valid Lua expression. The issue affects workspace clicks;
JSON read modules and the theme do not require a redesign.

The optional build prepared by the installer retains Waybar 0.12 and converts
only workspace requests to `hl.dsp.focus` / `toggle_special`.
It identifies itself as `hyprixe-lua-ipc1`. An upstream Waybar build that
already has both Lua IPC paths is reused without compilation.
The systemd drop-in points to the selected executable, including when it is
in `~/.local/bin`; backup/restoration of the executable is covered by tests.
No Waybar CSS or layout was changed.

Six additional tests cover capability detection and compile the small C++
adapter to submit its output to a real Lua interpreter: numeric workspaces,
names containing quotes/backslashes/newlines, workspace on the current
monitor, special workspaces and unchanged read requests.
All 32 tests pass. The full Waybar build and its capability check were performed
in Debian WSL, without opening a session.

Source comparison and instrumented tests do not replace `hyprctl configerrors`
in a 0.56.2 session or physical testing of dragging, resizing, focus cycling
and locking. Those validations remain SKIPPED here.

Primary sources for the review:
[official 0.56.2 example](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua),
[bindings/dispatchers](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsDispatchers.cpp),
[option registry](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/values/ConfigValues.cpp),
[IPC handling](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/debug/HyprCtl.cpp),
[Waybar 0.12 clicks](https://github.com/Alexays/Waybar/blob/0.12.0/src/modules/hyprland/workspace.cpp),
[upstream Waybar Lua backend](https://github.com/Alexays/Waybar/blob/master/src/modules/hyprland/backend.cpp),
[Hyprlock 0.9.6 parser](https://github.com/hyprwm/hyprlock/blob/v0.9.6/src/config/ConfigManager.cpp).

## October 26 follow-up: Waybar entry point and XDG regression

The target PC reported a missing `hypr/waybar/config` file during
`test_custom_xdg_paths_are_rendered`, followed by an unhandled exception in
the verifier. In the source checkout, this file was only a JSON include wrapper
pointing to `hypr/waybar/configs/Frosted-Glass`; both launch paths still used
the wrapper. It contained no independent settings.

The direct launcher and systemd drop-in now both select `configs/Frosted-Glass`
explicitly with `-c`, alongside `style.css` with `-s`. The redundant wrapper was
removed from the repository and is no longer synthesized during deployment.
Custom XDG paths, including spaces, are checked against the actual copied
configuration and the rendered service arguments. Existing personal wrapper
files are left alone and are not used by these launchers. The Frosted Glass
configuration and stylesheet contents were not changed.

The deployment test now checks the actual JSON file, CSS files and service
arguments. Direct-launch tests also check that the files passed to Waybar
exist, so a command mock cannot silently accept a nonexistent configuration.
Additional regression tests cover launching with custom XDG paths without a
wrapper, rejecting incomplete Waybar payloads before any configuration writes,
and reporting missing/invalid JSON, TOML or XML without aborting the format
checks. A genuinely missing active configuration still produces a failure.

Validation is rerun from the available Debian 13 WSL environment, not remotely
on the user's physical PC. The real desktop dependency check remains enabled:
missing local Hyprland/desktop commands and the Qt6 Kvantum plugin must still
cause `--dependencies` to return a nonzero status here. No desktop dependencies
are mocked or waived to obtain a passing result. The target PC must rerun
`./verify.sh --dependencies` after receiving these changes.

Final commands were run with the previously built awww/Rofi/Waybar executables
in PATH, without modifying desktop dependency detection:

| Command | Result on the final code |
| --- | --- |
| `./verify.sh` | 38 tests OK; Bash, ShellCheck, 82 Lua files, format parsers, Rofi, Lua IPC, asset hashes and native-profile checks pass; `RESULT: 0 failed check(s)`, exit code 0 |
| `./verify.sh --dependencies` | The same 38 tests and repository checks pass; only `Installed runtime dependencies` fails because this WSL environment lacks Hyprland/desktop commands and the Qt6 Kvantum plugin; `RESULT: 1 failed check(s)`, exit code 1, no traceback |
| `git diff --check` | Exit code 0, no whitespace errors |

The physical Debian PC's dependency result has not been observed from this
terminal. A zero-failure result for that machine is not claimed here.

## Physical-PC report: Git checkout portability and runtime selection

The user subsequently supplied a physical Debian PC report with a broken
`style.css`, unavailable awww, X11-only Rofi, a Waybar without Lua workspace IPC,
and an asset-hash failure. That report supersedes the earlier absence of
target-machine output; the commands below are still agent-run Linux/WSL checks.

Two repository defects were reproduced from an actual Linux `git archive HEAD`,
independently of the Windows working tree:

- Git stored `hypr/waybar/style.css` as mode `120000`, with CSS import text as
  the symbolic-link target. Windows with `core.symlinks=false` exposed the blob
  as an apparently usable regular file, hiding the Linux failure. Its Git mode
  is now `100644`; the CSS content is unchanged.
- The original inventory matched the raw CRLF bytes of both Kvantum files and
  Dolphin's toolbar. Git had normalized their blobs to LF, so clean Linux
  checkouts failed the exact hash checks. Attributes now disable normalization
  for these three assets, and the stored blobs contain the original bytes.
  No colors, SVG elements or toolbar actions changed. Hash checks remain strict
  and now report each path, expected hash and actual hash on a mismatch.

The verifier now examines dangling links before filtering readable files. A
source failure stays a FAIL and prevents the dependent deployment suite from
producing repeated fixture tracebacks. Missing or changed real assets still
fail. `verify.sh` uses the same `~/.local/bin` priority as installation and the
session. Rofi capability detection is shared by the builder, dependency checker
and verifier. An X11-only build is an explicit runtime failure, with theme
parsing SKIPPED until a suitable Wayland build is available.

Regression coverage includes the invalid CSS-text symlink, missing source CSS,
per-asset failures, and headless Rofi capability probes. The working-tree suite
passes all **48 tests**. A separate Linux export of the prospective Git tree is
also checked as an unprivileged user without DISPLAY or WAYLAND_DISPLAY, with
the real previously built binaries placed in that user's `~/.local/bin`.

The physical PC must receive these changes and rerun `./install.sh native`
if runtime capabilities are still missing, followed by `./verify.sh --dependencies`.
`--no-packages` is unsuitable for preparing missing runtime binaries. No VMware
profile or graphics-rendering variable was changed by these fixes.

Observed results for that exported Git tree (not a copy of the Windows files):

| Command / check | Result |
| --- | --- |
| Linux extraction of the old HEAD | Reproduced the dangling CSS-text symlink and all three line-ending-only asset hash mismatches |
| Linux extraction of the corrected prospective tree | Regular `style.css`; all four original asset SHA256 values match |
| `./verify.sh`, UID 65534, no graphical display | 48 tests OK, with the root-only fixture SKIPPED; all six real Rofi parser checks pass; exit 0, zero failures, no traceback |
| Same export, `./verify.sh --dependencies` | Only the unavailable WSL desktop dependencies fail; Rofi, Waybar and both awww executables resolve to the temporary user's actual `~/.local/bin`; no traceback |

The previous validation had not checked the Linux representation of the Git
tree and therefore missed these repository defects. The verifier now also
checks the Git mode of `style.css` explicitly, including on Windows.

## XKB stable/backports build dependency regression

The target PC reported XKB runtimes `1.13.1-1~bpo13+1` with APT attempting to
install stable `1.7.0-2` headers. Debian's metadata confirms that the development
packages require exactly matching runtime versions, and that
`libxkbregistry-dev` also requires the matching `libxkbcommon-dev`.

`scripts/apt-build-deps.py` now selects headers by installed backports source
family, including indirect development dependencies. Waybar explicitly lists
both XKB headers. The same planner is used by the awww and Rofi build steps.
Only matching headers use `/trixie-backports`; the rest retain normal APT
selection. Build dependency transactions prohibit removals and downgrades.
Planner failures stop the build; no process-substitution failure is ignored.

Real APT tests were run in Debian 13 WSL, with actual Debian packages rather
than mocked package status:

| Command / scenario | Observed result |
| --- | --- |
| Planner simulation before the upgrade, XKB runtime/dev `1.7.0-2` | Resolver exit 0; headers stay on stable |
| Remove the test environment's XKB headers, then install `libxkbcommon0/trixie-backports libxkbregistry0/trixie-backports` | Both runtimes actually installed at `1.13.1-1~bpo13+1`; headers absent |
| Original Waybar build dependency command, `apt-get -s install ... libxkbregistry-dev ...` | Exit 100; reproduced the exact stable-header/backports-runtime conflict and attempted `1.7.0-2` downgrade |
| Corrected planner and `apt-get -s --no-remove -o APT::Get::allow-Downgrades=false install ...` | Exit 0; only the two XKB headers selected explicitly from backports; GTK/gtkmm/dbusmenu headers remain stable |
| Actual installation of that corrected dependency list | Exit 0; both headers installed at `1.13.1-1~bpo13+1`, both runtimes preserved at that version; no removals or downgrades |
| `dpkg-query -W` for the four XKB packages | All four actually installed at `1.13.1-1~bpo13+1` |
| `python3 scripts/apt-build-deps.py --simulate rofi` after the XKB upgrade | Exit 0; the shared selection also resolves Rofi headers |

The current Waybar dependency graph was inspected, including its indirect
headers. The selector covers other already-backported source families, such as
Wayland or XML, without forcing GTK, systemd or the rest of the system into
backports. A missing matching backport is a fatal error, not a stable fallback.
Seven unit regressions cover stable, XKB backports, indirect headers, unrelated
backports, removed packages, unavailable headers and failed metadata queries.

The updated `scripts/build-runtime.sh` was then actually run with the backports
XKB runtime/dev packages installed. It reused the real awww/Rofi binaries,
installed the selected Waybar build dependencies through APT, fetched the pinned
Waybar source and compiled all 124 Ninja steps successfully. The resulting
`Waybar v8490a1d (branch 'HEAD') (hyprixe-lua-ipc1)` passes the Lua workspace IPC
capability check. The binary and full build/APT logs are outside the repository.
No graphical session or physical GPU test is claimed for this build test.

Final `./verify.sh` with the previously built runtime tools in PATH: **55 tests
OK**, Bash/ShellCheck/Lua/format/asset checks pass, `RESULT: 0 failed check(s)`,
exit 0. `git diff --check` also exits 0. Desktop dependency/session checks remain
subject to the earlier WSL limitations; the real APT and Waybar build scenarios
above do not use mocked package versions.

Primary references: [Debian's selective backports installation](https://backports.debian.org/Instructions/)
and [the libxkbcommon backports source package](https://packages.debian.org/source/trixie-backports/libxkbcommon).

## UWSM-managed Debian session integration

The user reported a working physical Hyprland session and imported activation
variables, but inactive `graphical-session.target`. Debian's Waybar service
therefore failed its `Requisite=` dependency. Importing an environment and
starting a compositor do not by themselves establish the UWSM lifecycle.

The actual Debian packages were inspected: the plain `hyprland.desktop` runs
`/usr/bin/start-hyprland`; `hyprland-uwsm.desktop` is named
`Hyprland (uwsm-managed)` and runs `uwsm start -e -D Hyprland hyprland.desktop`.
UWSM `0.26.7+ds-2~bpo13+1` was actually installed from backports in the test
environment. The updated six-package backports list resolves with APT exit 0.
Debian's Waybar, Hypridle and SwayNC vendor unit files were also inspected.

The startup hook now finalizes its environment with UWSM and queues the Hyprixe
service target without blocking compositor startup. Only UWSM activates the
graphical target. Debian Waybar's `PartOf=`, `After=` and `Requisite=` remain
intact; its drop-in selects the existing Frosted Glass paths and app slice.
The target also requests the vendor idle/notification services and dedicated
units for the persistent awww daemon, wallpaper application, clipboard watcher
and authentication agent. Their lifecycle is bound to the graphical session.
Static units read UWSM's session-specific environment file; Hypridle's lock
commands explicitly address `$XDG_SESSION_ID` instead of relying on the PID
of a systemd user service to identify the login session.

Alacritty, Dolphin, Rofi and Hyprlock launch through `uwsm app --`; Rofi uses
that prefix for selected applications as recommended upstream. Short control
commands and all 64 keyboard/mouse combinations are preserved. Logout uses
`uwsm stop`. `--session` adds read-only diagnostics for UWSM, the graphical
target, activation environment and each session service. It never starts a
target or edits dependencies to make a failing check pass.

Validation performed:

- All 69 unit/integration tests pass, including unmanaged sessions with already
  imported variables, an inactive graphical target, stale manager environment,
  failed Waybar, read-only diagnostics, GUI argument preservation, UWSM startup
  ordering, managed wallpaper startup and orderly logout.
- The complete native Lua graph still loads with 64 unique bindings and the
  required mouse/Alt+Tab callbacks. Six real Rofi parser checks accept the
  configuration, including the application launch prefix.
- A dedicated temporary Linux user and real systemd user manager were used
  with the packaged UWSM and the actual Debian vendor service dependencies.
  The rendered units passed `systemd-analyze --user verify`.
- Before UWSM startup, an actual `systemctl --user start waybar.service` failed
  with dependency result while `graphical-session.target` remained inactive.
- The actual UWSM startup/finalization handshake activated the graphical target,
  then `hyprixe-session.target` and all seven requested services became active.
  The wallpaper oneshot completed while its separate daemon remained running.
  The new session diagnostic function passed against the real user manager.
- The real `uwsm app` command placed the terminal fixture in
  `app-graphical.slice`. The real `uwsm stop` deactivated the graphical target
  and every managed unit, and all daemon/application fixture PIDs disappeared.
  The temporary account was removed and the host user manager was unchanged.

The live service-lifecycle test deliberately used a compositor stand-in, GUI
daemon/clipboard stand-ins and synthetic login-session metadata because WSL
does not provide an SDDM VT login. UWSM, D-Bus, systemd, dependency ordering,
service activation and cgroup teardown were real. Earlier harness attempts
without login/seat metadata stopped in UWSM's environment preloader; these
were test-environment limitations, not fixed by changing production targets.
No physical SDDM login, Wayland rendering, PAM unlock or suspend/resume is
claimed as tested here. Those checks remain for the target Debian PC after
selecting the managed session.

Final checks on the delivered code: `./verify.sh` exits 0 with 69 tests OK,
133 Bash syntax checks, both ShellCheck levels, 82 Lua syntax checks, six real
Rofi parser checks, original asset hashes and Git modes passing. The live
unit/cgroup harness also passes with a home directory containing spaces.
A CLI regression using synthetic current-Hyprland variables and a real inactive
UWSM/user manager makes `./verify.sh --session` return the expected nonzero
status with two clear SDDM/graphical-target diagnostics and no traceback.
`git diff --check` and `git diff --cached --check` both pass.

References: [Hyprland UWSM integration and application scopes](https://wiki.hypr.land/Useful-Utilities/Systemd-start/),
[UWSM startup, environment and shutdown](https://github.com/Vladimir-csp/uwsm),
and the Debian-packaged unit/desktop files inspected above.

## Persistent workspaces 1–4

Waybar now uses `persistent-workspaces: {"*": [1, 2, 3, 4]}` with numeric
sorting. Explicit IDs avoid the monitor-ID offsets of a wildcard integer
count in Waybar 0.12. The compositor independently loads four concrete
`hl.workspace_rule({ workspace = tostring(id), persistent = true })` entries.
There is no monitor field, range selector, startup workspace-switching script
or CSS change. Workspaces 5–10 remain available dynamically.

The v0.56.2 Lua rule parser and workspace placement controller were checked:
the boolean persistence rule creates missing concrete workspaces, marks them
persistent and uses an available/focused monitor when no monitor is specified.
The Lua load test records all four rules and rejects missing/duplicate IDs or
monitor bindings. A deployment regression also checks the installed Waybar IDs
and executes the installed Lua graph when Lua is available.

Actual validation: `./verify.sh` exits 0, 70 tests OK, 83 Lua files parsed,
64 unique bindings retained; `git diff --check` passes and the Waybar stylesheets
are unchanged. Live `hyprctl`/visual confirmation remains SKIPPED without a real
Hyprland session in this environment.

Primary sources: [Hyprland 0.56.2 workspace rules](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsConfigRules.cpp),
[persistent workspace creation](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/state/WorkspacePlacementController.cpp),
[Waybar 0.12 explicit persistent IDs](https://github.com/Alexays/Waybar/blob/0.12.0/man/waybar-hyprland-workspaces.5.scd).

## SDDM Frosted Glass theme — October 26, 2026

Environment: Debian 13 under WSL2. Qt 6.8.2 and the native Debian SDDM greeter
from `sddm 0.21.0+git20250502.4fe234b-2` were used. The SDDM package was downloaded
and extracted for test-mode rendering, not installed or started as the system
display manager. No physical SDDM/PAM login or Hyprland session was started.

The new theme is original QML in `sddm/themes/hyprixe-frosted/`, using the existing
wallpaper. No files under `.config/`, `.local/` or `profiles/` changed in this
SDDM work. UWSM session files, Waybar fixes and keyboard bindings remain intact.

| Command / check actually executed | Observed result |
| --- | --- |
| `./verify.sh`, with the previously built Rofi/Waybar/awww in PATH | Exit 0; **89 tests OK**, 133 Bash scripts, 83 Lua files, both ShellCheck levels, six real Rofi parses, original asset hashes and source/security checks pass |
| `/usr/lib/qt6/bin/qmllint --ignore-settings --unqualified info` on `Main.qml` and the three components | Exit 0. Only informational notices for SDDM-injected `config`, `sddm`, `userModel` and `sessionModel`; syntax/import/property checks are not disabled |
| `python3 -m unittest discover -s tests -v` through the verifier | Includes **19 new SDDM tests**: system transactions, combined user/system restore, root CLI lock/backup flow, and actual Qt controls/context models |
| Qt interaction child process: `tests/sddm_qml_smoke.py`, offscreen/software Qt backend | Actual Qt 6 `QAbstractListModel` roles and Controls load with zero runtime warnings. Last user/session retained; chosen session index forwarded unchanged; errors clear the password; duplicate login blocked; account/session popups open; power methods reach only the mocked proxy; empty user/session models handled |
| Same Qt layout test at 1920×1080, 1280×720, 1024×768, 800×600 and 3840×2160 | Controls remain usable and inside the horizontal layout; small screens retain scrolling. This test does not validate shader rendering |
| Extracted `sddm-greeter-qt6 --test-mode --theme STAGED_THEME`, on a dedicated Xvfb display using Qt's xcb backend | Theme loads in the real Debian greeter. Rendered captures were examined at 1920×1080, 1280×720, 800×600, and 3840×2160 with `QT_SCALE_FACTOR=2`. Wallpaper, cyan borders, dark translucent panel, GPU blur, rounded corners, clock/date and footer render correctly |
| System installation/restore in a temporary filesystem, including the privileged CLI path | Exact wallpaper copy, effective theme selection, dated backups, no-op repeat, permissions, owner restriction, unchanged UWSM entry, other themes/personal files preserved; corruption, changed files, source absence, symlinked targets/state and injected disk errors handled |
| Combined user/system transaction tests | Root backup linked to user restore; system-only change creates a restore transaction; failed system install rolls user files back; conflict in either scope prevents the other scope from being restored |
| `apt-get -s install --no-remove` with the eight packages in `packages-sddm.txt` | Exit 0; Qt modules already installed at the expected stable Qt 6 versions; no removals or downgrades |
| `./verify.sh --dependencies` in this WSL environment | Exit 1, **3 expected failed check groups**, no verifier traceback: no installed system SDDM theme, no installed SDDM daemon/greeter, and missing desktop runtime dependencies. Repository tests still all pass; this is not a successful deployment check on the physical PC |
| `git diff --check`, current/untracked file review | No whitespace errors or generated runtime assets added to the repository; no commit made |

The native greeter preview correctly reports an empty session directory in the
test environment, disables login, and uses the fallback avatar. Its missing
default face-image warning and absent daemon-socket notice are expected in this
isolated test-mode setup. Session choice and power dispatch were exercised with
explicit Qt model/proxy fixtures, not real authentication or shutdown. Xvfb,
staging copies, logs and captures remain outside the repository. The original
wallpaper is present only once as a source asset; installation copies it into
the system theme so the greeter does not need access to a user's home directory.

Still required on the physical Debian PC:

1. Run `./install.sh native`, then `./verify.sh --dependencies` to validate actual
   installed files, effective SDDM configuration and available UWSM entry.
2. Reboot; inspect the real greeter on the GPU, outputs, resolutions and DPI settings.
3. Test actual account selection/avatar, keyboard layout/password entry, failed
   authentication and successful PAM login into **Hyprland (uwsm-managed)**.
4. Inside that session, run `./verify.sh --dependencies --session`; confirm the
   UWSM graphical target and Waybar/session services after a real SDDM login.
5. Check the greeter's power menu and multi-monitor behavior when convenient.
   A windowed/offscreen preview cannot establish hardware shutdown or seat behavior.

Recovery is documented in [INSTALL.md](../INSTALL.md#recover-only-the-previous-sddm-theme):
`./uninstall.sh --sddm-only` restores the previous login theme from its private
system backup, including from a TTY, without restoring personal desktop files.

## Physical keyboard and login transition follow-up — October 26, 2026

The physical PC's SDDM/UWSM journals were requested but were not available during
this follow-up. The accessible terminal is still Windows/WSL. Its actual
`journalctl -b -u sddm` has no entries, `graphical-session.target` is inactive,
and the normal user's Hyprixe target is absent. These facts describe WSL, not
the affected PC; no definitive cause of that machine's white flash is claimed.

Confirmed source findings:

- The theme does not instantiate `InputPanel` or import Qt Virtual Keyboard,
  and does not call `Qt.inputMethod.show()`. Password focus remains a normal
  Qt Quick TextField. The installed snippet now explicitly writes
  `[General] InputMethod=`. Higher-priority overrides are backed up/neutralized
  and restored through the existing transaction system.
- SDDM's Debian greeter source closes its view on `loginSucceeded`; the theme's
  handler only clears the password. No extra greeter-hide window, artificial
  delay, backend change or PAM/session change was added.
- Hyprland 0.56.2's upstream default clear color is `0xff111111`, not white.
  Hyprixe now explicitly uses the matching SDDM navy `rgb(122434)` and disables
  the built-in splash before the wallpaper layer is present. This is a palette
  choice, not proof that the previous clear color caused the reported flash.
- The old wallpaper helper imposed a one-second fade while visible services
  could start in parallel with it. The static image is now requested without
  that animation. Waybar/SwayNC pull in the wallpaper oneshot and wait for it;
  the oneshot requires the persistent awww daemon and the active UWSM target.
  The user unit reload precedes UWSM finalization, including for an already
  enabled Debian Waybar unit. Early monitor callbacks defer to the managed unit.
- No fullscreen application is launched by the repository startup graph.
  User/system XDG autostarts and transient fullscreen clients on the physical
  PC remain possible sources requiring its journals and observations.

Validation actually executed:

| Command / scenario | Observed result |
| --- | --- |
| `./verify.sh` with the previously built graphical binaries in PATH | **101 tests OK**, zero failed checks; 133 Bash scripts, both ShellCheck levels, 83 Lua files, required shortcuts/four workspaces, Qt 6 QML, Rofi parses, original asset hashes and native/secret scans pass |
| New SDDM tests | Explicit empty input method despite top-level/later overrides; exact restoration of old values and unrelated settings; reenabled input method detected; forced QML keyboard import/panel/show call detected |
| Qt 6 runtime smoke test | A keyboard key event enters the password field normally; existing login, selected session, failure/password clearing, power and responsive-layout cases still pass with the mock SDDM proxy |
| Wallpaper/runtime regressions | No startup fade; inactive early UWSM target starts no daemon; an initially empty monitor query is retried only until ready; bounded IPC failure remains nonzero; one daemon, all outputs, no forced restart |
| Unit/read-only checks | Source dependencies and installed drop-ins checked; missing loaded ordering and premature activation timestamps fail; a later manual wallpaper restart skips original chronology instead of producing a false failure |
| Actual packaged UWSM/systemd integration in a disposable account | `systemd-analyze --user verify` passes using Debian vendor Waybar/Hypridle/SwayNC units; normal and already-enabled Waybar startup both pass; actual `uwsm stop` deactivates the target/services and terminates all process fixtures |
| Already-enabled Waybar monotonic timestamps, in microseconds from the isolated test | Wallpaper oneshot active at **3553488**, SwayNC began activation at **3555370**, Waybar at **3555847**. This establishes request/service ordering, not physical monitor presentation |
| `python3 scripts/session_diagnostics.py` in WSL | Report completes without traceback; unavailable compositor/awww IPC and inactive/missing units are explicit; no services or processes changed |
| `./verify.sh --dependencies` in WSL | All 101 repository tests pass; **4 expected failed check groups** for absent installed SDDM theme, SDDM runtime, deployed user units and desktop runtime dependencies. Exit 1 without traceback; not presented as validation of the physical PC |
| `git diff --check` and source review | No whitespace findings, caches, logs, secrets or temporary fixtures added; no commit made |

The integration harness uses real UWSM, systemd, D-Bus and vendor unit
dependencies with explicit compositor/application stand-ins. It does not start
SDDM, authenticate through PAM, render a real Hyprland frame, test a physical
keyboard/VT transition, or prove that the white flash disappeared. The existing
100 ms / at most 5 s polling is solely for IPC/output readiness and was tested
to stop after readiness; no new unconditional sleep was introduced. The unit's
15 s startup timeout bounds failures rather than delaying a successful start.

On the PC, apply [the documented update](../INSTALL.md#login-transition--white-flash-diagnosis),
reboot, test password focus/typing, then run
`./verify.sh --dependencies --session --diagnostics` inside the managed session.
If the flash persists, correlate the physical SDDM/user monotonic journals,
startup-hook log, current clients/layers and autostarts with its appearance.
An after-the-fact snapshot cannot identify an already disappeared window or its
pixel color. Visual confirmation on the affected hardware is still required.

Primary references: [Debian SDDM InputMethod and configuration precedence](https://manpages.debian.org/trixie/sddm/sddm.conf.5.en.html),
[Debian greeter revision](https://github.com/sddm/sddm/blob/4fe234b/src/greeter/GreeterApp.cpp),
[Hyprland 0.56.2 clear color/configuration](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/values/ConfigValues.cpp),
[Hyprland background renderer](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/render/Renderer.cpp).

## Waybar icon taskbar — October 26, 2026

The existing Waybar build (`8490a1d`, `hyprixe-lua-ipc1`) contains `wlr/taskbar`
and `zwlr_foreign_toplevel_manager_v1`. Hyprland v0.56.2 advertises version 3 of
that protocol and activates the selected window through its native handle. No
Hyprland IPC fallback, window-management changes, keybindings, services or new
runtime packages were needed. Build/dependency checks now require this compiled
module as well as the existing Lua workspace support.

Only the new JSON module and `#taskbar` CSS rules affect the visible bar. The
workspace configuration, every existing module, overall layout/height and other
CSS rules remain unchanged. Each toplevel has a separate icon, with the title
available on hover and an active-state fill/outline. There is no app grouping
that would prevent selecting a particular window.

Validation actually performed under Debian 13 WSL:

- `./verify.sh`: **102 tests OK**, zero failed checks, including the compiled
  module/protocol capability regression, Bash/ShellCheck/Lua/QML checks, Rofi
  parses and unchanged original Frosted Glass asset hashes. The verifier also
  checks the icon-only/focus/tooltip configuration and active-state styling.
- Started the actual prepared Waybar with the complete updated JSON and CSS on
  an isolated Sway 1.10.1 headless compositor, with a private runtime directory,
  session bus and virtual pointer. A minimal read-only Hyprland IPC fixture
  supplied workspace/window metadata for the existing Hyprland-specific modules.
  **Taskbar enumeration, clicks, state changes and activation used the real
  Wayland foreign-toplevel protocol**, not that fixture.
- Three actual Qt Wayland window fixtures were opened: two with the same
  Alacritty app ID and one with the Dolphin app ID. GTK loaded the Breeze icons;
  their separate 16 px buttons and cyan active indicator were inspected in
  native rendered captures. Waybar kept its **1900×31** geometry on a 1920 px
  output with the existing 10 px left/right margins.
- Pointer clicks on each of the three buttons focused exactly its associated
  window, checked against the compositor's actual focused-window state. Moving
  one terminal to workspace 2 and clicking its icon activated that workspace
  and that specific terminal. Closing the other terminal removed only its
  toplevel while the remaining terminal and Waybar stayed running. The rendered
  active highlight moved with focus; the four workspace buttons remained shown.
- The isolated environment lacks some desktop services (MPRIS, audio and
  Bluetooth). Their unrelated module diagnostics were not treated as a taskbar
  failure; the bar still ran. GTK accepted the actual stylesheet without parse
  errors. Test-only Sway, pointer/IPC fixtures, packages, captures and logs are
  outside the repository and are not installed on the user's PC.
- `git diff --check` and final source review: no unrelated window/keybinding,
  profile, SDDM or service changes; no cache/test artifacts added; no commit made.

This is a real Waybar/Wayland integration test on a separate headless compositor,
not a live Hyprland 0.56.2 or physical GPU session. Confirm the actual application
icons, monitor scaling and native Hyprland focus/workspace behavior on the PC
using the procedure in [INSTALL.md](../INSTALL.md#waybar-application-icons).

Primary sources: [Waybar 0.12 taskbar interface](https://github.com/Alexays/Waybar/blob/0.12.0/man/waybar-wlr-taskbar.5.scd),
[Hyprland 0.56.2 protocol registration](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/managers/ProtocolManager.cpp),
[Hyprland native activation](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/protocols/ForeignToplevelWlr.cpp).

## Screenshot shortcuts — October 26, 2026

Reused the existing `ScreenShot.sh` helper. Added only `SUPER+SHIFT+S` (selected
area to clipboard), `Print` (full save) and `SHIFT+Print` (area save). Existing
`SUPER+Print` / `SUPER+SHIFT+Print` save-and-copy bindings and delayed/active-window/
optional editor modes remain. The new save modes use `~/Pictures/Screenshots/`;
legacy modes keep the XDG Pictures location. Timestamped destinations use
`mktemp` for atomic unique reservation, including concurrent same-second captures.
Selection happens before creating a screenshot directory. Clipboard writes occur
only after successful capture, and save-only modes leave the clipboard alone.

Actual validation in Debian 13 WSL:

- `./verify.sh`: **112 tests OK**, zero failed checks; 133 Bash scripts pass
  `bash -n` and both ShellCheck levels; 83 Lua files parse. The complete native
  Lua graph loads **67 unique chords**, including all five screenshot bindings
  and the existing workspace, mouse and Alt+Tab combinations.
- Ten new script regressions use a temporary HOME containing spaces and explicit
  command mocks. They verify PNG MIME/geometry arguments, copy-only without a
  saved file, full/area saves in the literal Pictures directory, unchanged
  clipboard on save/cancel/failure, four concurrent captures at one frozen
  timestamp, invalid arguments, cleanup of temporary/empty files and preservation
  of legacy XDG save/copy, countdown and editor behavior.
- Real tools were also exercised on an isolated Sway headless Wayland display
  using a private session bus/runtime directory and protocol-based virtual
  pointer. Actual `grim` produced a **1920×1080** full-desktop PNG in the requested
  directory. A real `slurp` drag selected a **301×201** area; `grim` captured it,
  `wl-copy --type image/png` owned the selection, and `wl-paste --type image/png`
  retrieved that PNG after the capture script exited, without an additional
  persistent file. The real area-save path created its PNG and left the previous
  clipboard bytes unchanged.
- Initial attempts to emulate a drag using Sway's deprecated cursor IPC cancelled
  the selector; the successful test used actual virtual-pointer motion/button
  protocol events. This was a test-input issue, not a change to the shipped
  selection script. All fixture code, test-only packages, logs and captures stay
  outside the repository. No Sway/virtual-input setup is deployed to the PC.
- Original Frosted Glass asset hashes, other component checks and `git diff --check`
  pass. No keybinding was removed and no service, profile, Waybar, SDDM or lock
  configuration changed. No commit made.

The real-tool test validates Wayland capture/clipboard behavior on a separate
headless compositor. Actual keyboard dispatch under Hyprland 0.56.2, the physical
Print key (including any laptop Fn behavior), monitor scaling and image pasting
into the user's applications still require a check on the PC. Apply and reload
using [the screenshot procedure](../INSTALL.md#screenshots).

## Native keyboard/mouse audit — October 26, 2026

The report and complete shortcut contract are in [KEYBINDS.md](KEYBINDS.md).
The physical Debian PC is not accessible through this workspace's terminal;
the following commands ran in Debian 13 **WSL**, not in the user's session.

Changes and verified causes:

- The old `cycle_next` followed by `alter_zorder(top)` changed the list traversed
  by the next cycle. This follows from both upstream implementations (0.55.2's
  compositor window vector and 0.56.2's `WindowQuery`/`WindowState`). A three-window
  regression reproduces z-order mutations and verifies the replacement uses all
  three windows in both directions. The replacement queries native Lua once per
  keypress, sorts by immutable creation ID, raises, then focuses a validated
  address. Empty/one-window, hidden/non-input clients, a closed active window,
  special workspace and fullscreen-blocked candidates are covered by the mock.
- Mouse actions remain native `window.drag()` / interactive `window.resize()`.
  Removed `opts.mouse`, which these Lua versions ignore. The old mock asserted
  that unsupported option; it now checks the actual actions.
- WindowSwitcher still uses a single client snapshot. Tests cover separate
  windows of the same application, invalid address/index, cancellation, managed
  Rofi precedence, abnormal Rofi errors and Lua errors returned with status zero.
  The selected window is raised before focus so floating windows remain visible.
- The live audit checks all 67 JSON rows and their real retained Lua handles,
  including enabled state and physical codes missing from JSON. It checks
  modifiers, flags, submap, obvious conflicts, script permissions, installed-file
  drift, required commands, Rofi Wayland capability, compositor PATH, version
  and native query/dispatcher APIs. It never invokes actual bound window actions.

Actual commands/results:

- `./verify.sh`: **134 tests OK**, **0 failed checks**, exit 0. All **133 shell
  scripts** pass `bash -n` and both ShellCheck levels. **83 Lua files** parse;
  the complete load-graph regression records **67 unique bindings** and four
  persistent workspaces. Original theme hashes, Rofi parsing, SDDM QML lint,
  service-order checks and Waybar capabilities pass.
- `python3 -m unittest discover -s tests -p test_keybind_checks.py -v`:
  **17 tests OK**. These use explicit registry/command fixtures, including missing
  binds, duplicates, wrong modifiers/flags/submaps, disabled/removed handles,
  opaque physical-key rows, zero-exit IPC errors, timeouts, installed-file drift
  and parser isolation. A regression also proves that existing `configerrors`
  are captured before and never cleared by Lua probes: upstream evaluation
  resets that list, so probes are skipped while load errors exist.
  These tests do not claim physical input success.
- Actual `/usr/bin/Hyprland --verify-config -c <temporary config>` under UID 65534,
  with a temporary HOME/XDG path containing spaces: **exit 0 / config ok**.
  The installed binary is **0.55.2**, commit
  `39d7e209c79d451efab1b21151d5938289da838d`. The instrumented native parse reads
  **67 real `HL.Keybind` objects**: their emitted registry-equivalent rows have
  **zero contract errors**, all handles are enabled, and all actual dispatcher
  constructor variants are accepted. Only `no_op` is executed.
- The new `check_native_config` function was separately run as UID 65534 against
  that real binary: **PASS**. The root WSL invocation of the full verifier
  explicitly skips this check; it runs normally for the desktop user on Debian.
- Negative native parser tests append a deliberate disable/unbind to a temporary
  config: `set_enabled(false)` and `hl.unbind("ALT + Tab")` are **rejected with
  an explicit Disabled/removed assertion**, as intended. During development an
  expired-handle getter caused the 0.55.2 parser to segfault. The final probe
  checks its safe `HL.Keybind(expired)` string before accessing any property;
  native disable/unbind tests and the expired-object regression now pass.
- Exact v0.56.2 bind-option/dispatcher/IPC source blobs were checked against
  their Git tree hashes. Native query functions and `stable_id`, `address`,
  `hidden`, `accepts_input`, `fullscreen` properties were inspected in both
  0.55.2 and 0.56.2. A 0.56.2 binary is not installed in this WSL environment.
- `./verify.sh --dependencies --session`: repository checks/tests pass, but
  **6 failed check groups / exit 1** are expected in this WSL setup: SDDM system
  files; SDDM runtime; installed user units; missing desktop dependencies;
  missing active UWSM/Hyprland environment; unavailable live binding audit.
  There is no traceback and these are not suppressed or counted as success.
- `git diff --check`: passed. Git status reviewed; only source/docs/tests are
  changed, with no generated fixture, cache, log or secret committed. No commit
  made. Installer deployment already includes the edited Lua/scripts, preserving
  its existing dated backups/restore. No profile, theme, SDDM, Waybar, workspace,
  lock or UWSM service configuration was changed.

An attempt to start a real isolated Hyprland compositor in WSL failed at backend
creation because no usable DRM/GPU device is exposed. Consequently **physical
Alt/Tab/F10 delivery, focus effects, overlapping floating windows, fullscreen
behavior, mouse drag/release, workspace keys, screenshot input/clipboard and
the user's actual loaded registry still require testing on the PC**. The
algorithm defect is established; it does not prove the cause of a chord that
never triggers. Run the application/session procedure in KEYBINDS.md and collect
`./verify.sh --session --diagnostics` from the affected physical session.

## Dolphin layout — October 26–27, 2026

**Historical result: this layout was rejected and is superseded by the
interface-restoration/paint-only update below.** Its layout-enforcing checks
no longer apply.

Implemented the native layout documented in [DOLPHIN.md](DOLPHIN.md): 96 px icon
view, a 264 logical-pixel right column with Places/Devices above Information,
large previews and compact metadata, minimal toolbar, hidden classic menu/status
bar and hidden Folders/Terminal docks. The existing Breeze Dark icon theme and
original Kvantum theme remain. The inherited Dolphin toolbar is intentionally
adapted; its original hash remains in the historical inventory, while its current
XML/action contract replaces the previous byte-identity assertion. The original
wallpaper and Kvantum pair still pass their unchanged SHA256 checks.

Real compatibility findings, not just file-format assumptions:

- Debian 13's Dolphin is **25.04.3** (`4:25.04.3-1+deb13u1`), Qt **6.8.2**,
  KF6 XMLGUI **6.13.0**. Its statusbar setting is an enum (`Disabled`), and
  `dolphinstaterc [State]` controls dock placement. Without a saved state, the old
  preset left Folders and the optional Terminal panel visible alongside Places
  and Information. Merely changing Kvantum would not fix that layout.
- Baloo Widgets **25.04.0** resets metadata visibility if its version-13 marker
  is absent. Native KConfig geometry keys contain colons (`screen: Width` and
  `screen: Height`); parsing must use `=` as the only delimiter. Real GUI tests
  exposed both issues and the final checks handle them, including omitted
  default-true metadata values.
- Dolphin may migrate view properties from `.directory` into the containing
  directory's `user.kde.fm.viewproperties#1` attribute, omitting default fields.
  Deployment/restore now snapshots that exact attribute; strict restore detects
  changes, and the explicit preservation option saves current Dolphin files/
  metadata before restoring originals. Other xattrs and unrelated edits remain
  protected. The verifier accepts native default storage semantics and still
  rejects a real Details-mode override.
- `kdegraphics-thumbnailers` alone did not provide JPEG/image previews in the
  minimal test installation. Installing **kio-extras** made real thumbnails work
  in both the grid and Information panel. **udisks2** enabled normal Solid device
  enumeration and visible device rows. These are now explicit full/component
  dependencies. Version preflight uses Qt's offscreen platform so it also works
  before a Wayland display exists.

Commands actually run in Debian 13 WSL (not on the user's physical PC):

- `./verify.sh`: **157 tests OK**, **0 failed checks / exit 0**. This includes
  **133** Bash syntax checks, both ShellCheck levels, **83** Lua syntax checks,
  the unchanged 67-binding/four-workspace load regression, source format checks,
  Rofi parsing, SDDM QML lint, Waybar capabilities and original theme hashes.
- `python3 -m unittest discover -s tests -p test_dolphin.py -v`:
  **23 tests OK**. Covers source contracts, real Qt dock-state restoration at
  three window sizes, scoped deployment and idempotence, custom XDG roots/spaces,
  preserving geometry/bookmarks/other metadata, malformed XML, closed-app
  preflight, strict restore, saved runtime edits and native xattr migration.
  Mock-APT tests exercise missing component dependencies, repeat installation,
  `--no-packages`, and critical APT failure before any configuration write.
- Real `./install.sh native --dolphin-only`, then **actual Dolphin** on a private
  Sway headless Wayland compositor/session bus under UID 65534, then
  `./verify.sh --dolphin`, then
  `./uninstall.sh --save-dolphin-changes`: **all exit 0** in each final scenario.
  Original preference/state/toolbar bytes were restored after Dolphin's real
  runtime writes; no mock application was presented as Dolphin.
- Actual widget inspection records **`Kvantum::Style` / `kvantum`**, right-area
  visible Places and Information docks, hidden Folders/Terminal, icon-only
  toolbar with exactly Back/Forward/Up/location/Search/menu, a hidden menu bar,
  and icon-grid item geometry. Captures were inspected, including a selected
  JPEG rendered as an actual image preview with Type/Size/Modified metadata.
- Final real scenarios: **1920×1080**, a **1100×680** floating window on
  **1366×768**, and **3840×2160 at scale 2**. The latter reports native device
  pixel ratio **2**; dock widths remain **264 logical pixels**. Places scrolls
  when a smaller window cannot fit all bookmark/device rows.
- `git diff --check`: passed. Changes reviewed; no inspector binary, fixture,
  screenshot, cache or log added to Git. The test instrumentation only observes
  widgets/captures inside the disposable process and is not installed by Hyprixe.
  No Hyprland, keybind, UWSM, Waybar, SDDM, Rofi, lock or profile file changed.
  No commit made.

The component installer can install missing dependencies with narrowly scoped
APT commands; it uses no sudo when they already exist. Full installation still
includes Dolphin. Backups keep their normal conflict protection, with
`--save-dolphin-changes` limited to managed Dolphin paths/its view xattr.

The requested reference screenshot is not present in this conversation; the
repository's existing desktop screenshot shows a terminal rather than Dolphin.
The requested layout was implemented and tested, but pixel-identical reference
comparison, the real Hyprland blur/transparency and the user's monitor/font/DPI
combination still need observation on the physical PC. No physical device was
mounted, ejected, unmounted or formatted during these tests.

## Dolphin interface restoration and translucent paint — October 27, 2026

Supersedes the rejected `9259fa5` layout above. Git parent `5d87b34` provides the
exact original tracked `dolphinrc` and `dolphinui.rc`; their hashes now pass the
source verifier. The view/dock/Baloo presets and Qt layout generator are removed.
The PC's own former state is restored from its installer backup, never replaced
by another generated layout. Only native color selection is then merged into
`dolphinrc`. Other Hyprixe configuration and original wallpaper/Kvantum hashes
remain unchanged. No Hyprland rule or graphics workaround was added.

Two actual causes of the white/light appearance were reproduced:

1. The original Kvantum SVG paints white opaque window interiors even with
   translucency flags enabled. The Dolphin-only SVG now paints blue with alpha.
2. KDE's application color manager reapplies a light palette after Kvantum starts.
   In the first real run the widget style was already `Kvantum::Style`, yet the
   application palette was `window=#eff0f1, text=#232629`. Selecting the matching
   per-application KDE scheme yields `window=#203f52, text=#e2eff5,
   highlight=#237e98` without changing the global color scheme.

Commands actually executed in Debian 13 WSL:

- `python3 -m unittest discover -s tests -p test_dolphin.py -v`:
  **32 tests, OK, exit 0**. Includes XDG paths with spaces, style-only installation
  and repeat, preservation of interface/state/xattrs/bookmarks, restored baseline
  defaults on fresh installs, backup-based UI rollback, missing/corrupt backups,
  rollback after a simulated disk failure, repeated-migration marker, native
  color-key-only uninstall preserving later UI edits, manual color conflicts,
  preview/device runtime and mock APT failure handling. Source tests compare all
  non-paint Kvantum options and SVG geometry with the original theme.
- `./verify.sh`, with the prepared native validation runtime on PATH:
  **166 integration tests OK; RESULT: 0 failed check(s), exit 0**.
  Bash syntax: **133 scripts**. ShellCheck: all scripts at error severity and
  active scripts at warning severity. Lua syntax: **83 files**. Existing
  keybindings/workspaces load test, Waybar/taskbar compatibility, SDDM QML lint,
  Rofi parsing, references, original-asset hashes and secret scan all pass.
  Actual Hyprland parser/live checks remain SKIPPED in this root WSL run.
- `./verify.sh --dolphin` in each isolated deployed desktop fixture:
  **0 failed checks, exit 0**. The actual Qt6 style probe instantiates Kvantum
  and resolves the Dolphin variant palette, with no forced fallback.
- External disposable GUI harness `hyprixe-dolphin-style-gui.py`: starts real
  **Dolphin 25.04.3 / Qt 6.8.2 / Kvantum 1.1.4** on private Sway headless Wayland
  and a private session bus as UID 65534. First observes the old interface, runs
  the actual archived `9259fa5` component installer, then runs the corrected
  `./install.sh native --dolphin-only --restore-dolphin-interface --no-packages`.
  Original UI files match their saved bytes before the paint step, apart from
  the new native ColorScheme key. The real widget inspection retains dock
  areas/visibility, toolbar actions and icon-grid metrics. Qt save/restore can
  round split heights by a few pixels; no dock geometry is imposed by the theme.
- The complete GUI install/verify/uninstall sequence passes at **1920x1080**,
  a **1100x680** window on **1366x768**, and **3840x2160 at scale 2** with an actual
  JPEG preview. Each phase launches the real application, not a mocked Dolphin.
  The native hamburger menu opens with **22 actions** and light text; its capture
  was inspected. A separate Qt application reports the identical original palette
  before/after. Paint uninstall restores the previous theme association and
  ColorScheme without changing the recovered interface or later runtime state.
- Alpha evidence at 1920x1080: `WA_TranslucentBackground=true`, minimum rendered
  alpha **198/255**, and **832,906 of 986,348** window pixels have intermediate
  alpha. The composited capture visibly shows `min_forest.jpg` through Dolphin.
  At scale 2, **3,528,448 of 3,945,392** pixels have intermediate alpha. Qt's raster
  Wayland window reports an unspecified GL alpha-buffer size (-1); no GL buffer
  depth is inferred from that value. Actual pixels/composited output establish
  translucency. The Sway harness does not provide Hyprland blur.
- `git diff --check`: passed. No fixture HOME, inspector, compiled binary,
  screenshot, log, cache or backup is added to Git. No commit made.

Remaining physical checks: run `./verify.sh --dolphin --session` inside the actual
UWSM Hyprland session, confirm its manager and running Dolphin export
`QT_STYLE_OVERRIDE=kvantum`, then inspect the exact restored personal layout,
blur, active/inactive opacity, contrast, context menus and monitor scaling.
This environment is Windows with Debian WSL, not the user's physical PC. Its
Hyprland GPU backend cannot run here; no live physical blur, UWSM environment or
physical mouse/keyboard test is claimed. Other desktop components were covered
by their existing regression checks, not relaunched as a physical desktop.
