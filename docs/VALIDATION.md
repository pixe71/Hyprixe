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

## Dolphin neutral light palette — October 27, 2026

Palette-only follow-up to the accepted blue variant in `0a92888`. Dolphin uses
neutral off-white `#e7e9e8`, gray panels `#d5d9d8`, dark text `#2d3437`, secondary
gray `#697477`, pale-blue selection `#c4dce2` and muted cyan links `#528a98`.
The existing application association and color-scheme name remain unchanged.

- Comparing the SVG with HEAD after masking RGB values yields identical bytes:
  every alpha/opacity, path, size and rendering parameter is retained. A frozen
  regression hash now enforces this contract. Palette base/alternate alpha stays
  `d1`; all non-color Kvantum settings match HEAD. No Hyprland, compositor,
  layout, toolbar, icon-size, dock-state or installer code was changed.
- `python3 -m unittest discover -s tests -p test_dolphin.py -v`: **33 tests OK**.
- `./verify.sh` with the prepared validation runtime on PATH: **167 tests OK**,
  **RESULT: 0 failed check(s), exit 0**. Includes the existing Bash, ShellCheck,
  Lua, Waybar, SDDM, references, original-theme hashes and secret checks.
- The actual component installer (`native --dolphin-only --no-packages`) was
  run on an isolated Debian 13 Wayland fixture containing the accepted blue
  release. Existing interface/state files remain byte-identical before/after
  the palette update. Real Dolphin reports `Kvantum::Style`, off-white window,
  dark text and pale-blue selection; the screenshot and native menu were
  inspected. A separate Qt application retains its original palette. The
  component verifier passes. Uninstall restores the previous blue paint while
  retaining the current interface.
- Rendered intermediate-alpha pixels remain **832,906 / 986,348**, with minimum
  alpha **198/255**, matching the accepted blue run. The wallpaper remains
  visible. This is an isolated Sway test in Debian WSL, not the physical
  Hyprland compositor; physical blur is not claimed as visually retested.
- `git diff --check`: passed. No generated test artifacts or caches are tracked.

Apply after closing Dolphin with `./install.sh native --dolphin-only`; the
legacy interface-restoration flag is not part of this palette update.

## Waybar organization — October 27, 2026

The actual Hyprladus `config/waybar/config.jsonc` and CPU script were inspected.
Only functional grouping informs Hyprixe; no upstream CSS, separators, colors,
Arch commands, personal paths or 10-workspace definition are imported. The
original Frosted Glass CSS rules remain verbatim in their declaration values;
new selectors reuse them, with matched-width pairs centering the Debian logo.
Height remains 31 px; no Hyprland/blur/opacity/font-global setting changes.

Commands and actual results in Debian 13 WSL:

- `./verify.sh` with the prepared compatible runtime on PATH: **182 tests OK**,
  **RESULT: 0 failed check(s), exit 0**. Includes **133 Bash** syntax checks,
  both ShellCheck levels, **83 Lua** syntax checks, existing keybind/workspace,
  SDDM QML, Rofi, Waybar protocol, original-asset and secret checks.
- New tests exercise CPU hwmon discovery on arbitrary indices, Intel/AMD/CPU
  thermal zones, exclusion of GPU/NVMe/ambiguous ACPI, invalid/disappearing data,
  root `/` storage fallback, both readings unavailable, JSON/markup escaping,
  preserved CSS rules, exact module order/no duplicates, workspace filtering,
  scoped XDG paths with spaces, backup/restore/idempotence/dry-run and missing
  active assets failing before any configuration write.
- Actual `./install.sh native --waybar-only --no-packages` executed under an
  unprivileged disposable desktop account, with an existing bar and XDG paths
  containing spaces. A dated Waybar-only transaction is created; no SDDM/Dolphin
  or other component is deployed. Fontconfig resolves the bundled Debian glyph.
- Actual `systemd-analyze --user verify` passes for the existing vendor and
  rendered Hyprixe units. Starting Waybar outside a graphical session is
  deliberately refused by the existing dependency, as expected. No target is
  manually activated and no `Requisite` is removed.
- A real UWSM session owns a real headless Sway compositor, Waybar 0.12 with the
  existing Lua compatibility build, awww-daemon and wallpaper application.
  Hyprland IPC responses and unrelated notification/idle/polkit/clipboard
  processes are explicit fixtures. This is **not physical Hyprland testing**.
- Actual `systemctl --user restart waybar.service` and
  `systemctl --user status waybar.service`: **active (running)** before/after,
  different MainPID. Actual `./verify.sh --waybar --session`: **0 failed checks**.
  UWSM, graphical/session targets and wallpaper ordering all pass. Actual
  `uwsm stop` deactivates the target and all session services.
- A GTK inspector inside the real Waybar observes the native drawer states
  **closed/open/closed**, with a real D-Bus SNI fixture icon mapped only while
  open. Two real Wayland GTK windows appear separately in the native taskbar;
  delivering the native button-release handler changes actual compositor focus
  and the active taskbar class. No polling/window-switching script is involved.
- Output mode changes from **1920x1080 to 1366x768**. Measured bar dimensions
  are **1900x31** and **1346x31** (the unchanged 10 px side margins). The logo's
  midpoint is **949.5 / 672.5**, versus bar midpoint **950 / 673**: within the
  expected half-pixel rounding, for both drawer states. Native battery widgets
  are unmapped with no battery. A fifth IPC fixture workspace is excluded;
  buttons **1,2,3,4** remain present. Captures were inspected.
- No CPU sensor is exposed in this WSL fixture, so the actual module displays
  root storage usage. Temperature branches are tested using independent sysfs
  fixtures, not claimed as physical measurements. Bluetooth/battery absence
  emits native warnings and does not stop Waybar. Existing FontAwesome/playerctl
  dependencies were installed in the validation environment to reproduce the
  intended glyph/media behavior; no new runtime package requirement was added.
- Diagnostic logs were inspected, not suppressed. Waybar 0.12's Sway headless
  output-description parser emits a nonfatal `basic_string::_M_create`; a throw
  backtrace identifies `Client::handleOutputDescription`. The test-only SNI
  producer can emit an initial missing-icon message before properties arrive.
  Neither is a new Hyprixe configuration error, and both real icon rendering
  and service operation are separately verified. No patch or graphics workaround
  was added to production to hide these fixture limitations.
- `git diff --check`: passed. The only active config changes are Waybar and its
  isolated glyph font. No test account HOME, inspector, screenshots, logs,
  caches, binaries or fixture session configuration are added to Git. The
  deliberately bundled one-glyph TTF and its license/provenance are source assets.

Still requiring the physical PC: real Hyprland 0.56.2 workspace clicks/output
hotplug, monitor/HiDPI visual balance, long expanded drawer content/many windows,
actual CPU sensors and battery charging/low/critical states, Bluetooth/network
changes, the eye's idle behavior, calendar and real tray-app interactions. The
weekday follows the session locale (French when the locale is French). No
physical compositor blur test or destructive power action was performed.
See [WAYBAR.md](WAYBAR.md) for the scoped application/restore commands.


## Kitty terminal migration (2026-10-28)

The current terminal is Kitty. Earlier dated sections mentioning Alacritty
record tests performed before this migration; they are retained as history.
No Waybar, SDDM, Dolphin, Kvantum, wallpaper, service-ordering or compositor
blur/opacity rules were changed for this migration.

Commands actually executed in Debian 13 WSL:

- `apt-get install --no-remove --no-install-recommends -y kitty`: installed
  Debian `kitty`, `kitty-shell-integration` and `kitty-terminfo`
  **0.41.1-2+deb13u2**, with no removals or upgrades.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_terminal.py -v`:
  **7 tests passed**, including the real Kitty parser, invalid values,
  unknown options, unavailable parser and stale terminal integration.
- `./verify.sh`, with the prepared Waybar/Rofi/awww binaries first in PATH:
  **exit 0, 190 tests passed, RESULT: 0 failed check(s)**. This includes
  Bash syntax for 133 scripts, ShellCheck, syntax for 83 Lua files, the full
  native Lua load mock, Rofi parsing, deployment/rollback, custom XDG paths
  containing spaces, original asset hashes and the source security scan.
- An additional unprivileged call to `check_native_config()` used the actual
  installed **Hyprland 0.55.2** parser in an isolated temporary HOME:
  **passed**, including all 67 retained handles and dispatcher constructors.
  This is not an interactive Hyprland 0.56.2 session test.
- `git diff --check`: **passed**.

A native integration fixture outside the repository was also executed:
`/mnt/c/Users/lucto/AppData/Local/Temp/hyprixe-test-kitty-native.py`.
It uses a temporary user, real UWSM/systemd, headless Sway, real Waybar and
awww, and the **installed** `LaunchTerminal.sh` to run Debian Kitty. Results:

- A real native Wayland Kitty window was created, with `TERM=xterm-kitty`,
  `TERMINAL=kitty`, a valid `KITTY_WINDOW_ID` and the correct Wayland display.
- Passing `--directory` preserved a working directory containing spaces.
- The Kitty parent ran in an `app-uwsm-kitty-*.scope`; Kitty placed its child
  in its own `kitty-*-0.scope` under `app-graphical.slice` as expected.
- Waybar remained `active (running)` before/after a real service restart.
  Existing tray, taskbar, four workspace buttons and output resizing passed.
- `uwsm stop` stopped the graphical session, its services and the terminal
  child. No manual graphical target activation or sleep was added to Hyprixe.

The fixture uses simulated Hyprland IPC and stand-ins for unrelated desktop
helpers. Its Sway output-description warning and absent battery/Bluetooth
warnings are the existing fixture limitations described above. It cannot
validate Hyprland GPU blur, physical keyboard input or the final appearance
on the user's PC. The live `hyprctl binds` check on that PC remains pending.

The standalone `scripts/check-deps.py` preflight was also executed with the
prepared runtime PATH. Kitty and its font/parser checks passed, but the whole
preflight returned **1** because WSL lacks these other desktop commands:
`hyprlock`, `hypridle`, `wpctl`, `cliphist`, `swaync`, `nm-connection-editor`,
`blueman-manager`, `pavucontrol`, `brightnessctl`. A complete
`./verify.sh --dependencies --session` pass is therefore **not claimed** for
WSL or the user's physical PC. Run it after installation and a fresh
**Hyprland (uwsm-managed)** login on Debian.

Local evidence (outside Git):
`/root/.cache/hyprixe-validation/kitty-verify.log`, `kitty-session.log`,
and `kitty.png`.


## Wlogout integration (2026-10-28)

Scope: the four-action menu, one new shortcut and the `logout_dialog` blur
namespace. The Waybar power menu, global blur, existing shortcuts, profiles,
Kitty, Dolphin, Kvantum, SDDM, Hypridle and wallpaper configuration are unchanged.
See [WLOGOUT.md](WLOGOUT.md) for behavior, installation and restore.

Commands actually executed in Debian 13 WSL:

- `apt-get install --no-remove --no-install-recommends -y wlogout` installed
  official Debian **1.2.2-1**, without removals or upgrades. The existing
  `librsvg2-common` package supplies `libpixbufloader_svg.so`; a regression test
  covers the actual underscore filename so detection does not falsely fail.
- `python3 -m unittest discover -s tests -p test_wlogout.py -v`: **14 passed**.
  Tests cover logical scale/rotation, named UWSM service toggle, fixed command
  dispatch, confirmation/cancellation/failure, unmanaged logout rejection,
  four-object layout validation, missing assets before writes, repeated
  deployment and exact backup/restore with XDG paths containing spaces.
  Restore preserves personal files and restores the previous helper mode.
- `./verify.sh` with prepared runtime binaries in PATH: **205 tests passed,
  exit 0, RESULT: 0 failed check(s)**. Bash, ShellCheck, 83 Lua files, native
  GTK 3 CSS parsing, all existing application/theme checks and Git modes pass.
- `check_native_config()` as an unprivileged user: the real available
  **Hyprland 0.55.2** parser accepted the isolated config, **68 retained bind
  handles** and dispatcher constructors. This does not claim an interactive
  Hyprland 0.56.2 session was tested.
- `git diff --check` and `git diff --cached --check`: passed.

An external native fixture ran the deployed launcher with real UWSM/systemd,
Wlogout, awww and headless Sway, using a temporary unprivileged user:

- Exactly four buttons appear horizontally in the requested left-to-right
  order, with actual GTK widget geometry checked. The panel measures about
  70% of logical width and 26% of logical height. Native runs covered
  1366x768, 1920x1080 and 2560x1440 at scale 2; the four button widths differ
  by at most one pixel after the equal minimum-width adjustment.
- Actual `hyprixe-wlogout.service` creation and second-invocation stop pass.
  Escape sent through the Wayland virtual keyboard closes the real menu.
- SVG icons and translucent panel paint were captured in native screenshots.
  This Sway fixture does not validate Hyprland GPU blur.
- Actual `uwsm stop` shuts down the session, including the application slice.
  No real poweroff, reboot or PAM lock was executed.
- GTK arrow navigation and Enter were additionally exercised with actual
  X11 events under a private Xvfb. Right/Left move focus and Enter dispatches
  the selected Lock action to a harmless stand-in. GTK initially focuses Lock;
  there is no per-button permanent active CSS. In the Sway virtual-keyboard
  fixture, arrow events arrived but focus traversal was inconclusive; physical
  Wayland keyboard navigation remains an explicit target-machine check.

The fixture uses simulated Hyprland IPC and unrelated GUI helper stand-ins.
Initial Waybar service readiness passed. Repeated earlier runs of the combined
bar/widget observer fixture hit its existing headless resource/crash behavior;
final Wlogout input/geometry tests stopped the bar after its readiness check
rather than changing any production Waybar files. Test-only `wtype`, Xvfb and
`xdotool` tools are not Hyprixe runtime dependencies.

Both requested complete commands were also executed against the actual WSL
HOME, with **205 tests passing in each run**:

- `./verify.sh --dependencies`: exit 1, **11 failed environment checks**.
- `./verify.sh --dependencies --session`: exit 1, **15 failed environment checks**.

These runs correctly report that the WSL root HOME has no deployed Hyprixe
configs, no installed Hyprixe SDDM theme/greeter, several missing desktop
commands and no current Hyprland/UWSM session. They are not represented as
successful target-machine runs. `hyprctl configerrors` reports
`HYPRLAND_INSTANCE_SIGNATURE not set! (is hyprland running?)`; live compositor
validation is unavailable here. Run both commands on the physical Debian PC
after installing and reloading Hyprland. Blur, hover, keyboard input, PAM
unlock and actual logout/shutdown/reboot still require interactive validation.

Evidence outside Git: `/root/.cache/hyprixe-validation/wlogout-verify.log`,
`wlogout-dependencies.log`, `wlogout-session-verify.log`, `wlogout-session.log`,
`wlogout-report.json` and `wlogout.png`.

## Rofi wallpaper sidebar — 2026-10-28

The application launcher now uses a dedicated Rasi extension. Git confirms no
changes to the shared `config.rasi`, `0-shared-fonts.rasi`, Frosted Glass theme
or palette, or to Hyprland/layer rules, Waybar, Wlogout, Kitty, Dolphin/Kvantum,
SDDM, profiles or the wallpaper asset. The centered window is 60% × 58%; the
wallpaper box is about 44% of content width, with four vertical icon buttons.

The pinned Rofi 2.0.0 source at commit
`0b6aa8ba8b4879f00c3cc96f2e47a13c079fe814` was checked out, submodules fetched,
and the guarded adaptation applied with:

```bash
python3 scripts/rofi_launcher.py --patch /path/to/validation/rofi-source
meson setup /path/to/validation/rofi-source/build /path/to/validation/rofi-source \
  --buildtype=release -Dwayland=enabled -Dxcb=disabled -Dimdkit=false -Dcheck=disabled
meson compile -C /path/to/validation/rofi-source/build
```

These are the build arguments actually used; paths above stand for the external
validation checkout, not files generated inside this repository. Compilation
completed successfully. Preparation is idempotent and rejects unknown source
before writes. The private `-hyprixe-launcher` argument gates both button return
codes and hover handling; it cannot leak through application environments.

An external fixture deployed the actual files for a temporary unprivileged user
with a HOME containing spaces, real UWSM/systemd, the prepared Wayland Rofi and
headless Sway. A persistent native virtual keyboard/pointer sent real input.
Harmless application executables and Hyprland IPC replies were test stand-ins;
no physical Hyprland session was used.

Results from that fixture:

- Immediate typing and Enter selected and launched a real native `drun` desktop
  entry through UWSM. Escape closed the launcher.
- Files and Terminal mouse clicks closed Rofi, then invoked the existing helpers
  in real UWSM scopes with `dolphin` and `kitty` respectively (safe executables).
- Applications returned from Run to `drun` in the same Rofi PID, retaining search
  focus. Windows opened the unchanged switcher after the first view closed;
  Enter produced its validated Lua focus request from one client snapshot.
- A normal Rofi `dmenu` invocation without the private argument returned upstream
  code 26 for custom action 17. Other menus are not opted into the extension.
- Screenshots were inspected at 1920×1080, 1366×768, 2560×1440 scale 2,
  3440×1440 and 5120×1440 scale 2: four round buttons inside the panel, blue/cyan
  hover, a covered proportionate wallpaper and rounded external corners.
- `uwsm stop` shut the temporary session down normally.

Earlier experimental fixture runs exposed Rasi's same-line string parsing and
font-driven text-button height; both were corrected before the final runs. A
Wayland media-query variant was discarded after it changed geometry between
opens; the final proportional layout uses no such conditional. Temporary
`wtype` devices also emitted nkutils keymap notices, so the final input tests
used one persistent virtual device. None of those fixture tools or experimental
files is deployed or added as a dependency.

Repository regression coverage includes native Rasi action/icon parsing, exact
source-patch guards and idempotence, fixed action dispatch, cancellation/errors,
custom XDG paths with spaces, installation/reinstallation, restored permissions
and missing installed assets without a traceback. The final runs used the
prepared binaries in PATH and `PYTHONDONTWRITEBYTECODE=1`:

| Command | Actual result |
| --- | --- |
| `./verify.sh` | Exit 0; **217 tests OK**, `RESULT: 0 failed check(s)` |
| `./verify.sh --dependencies` | 217 tests OK; exit 1, **12 environment checks fail** in the undeployed WSL root HOME |
| `./verify.sh --dependencies --session` | 217 tests OK; exit 1, **16 environment checks fail**, including no current Hyprland session |
| Native Rofi `-config FILE -dump-theme` | All eight Rasi files accepted, including the two new launcher files |
| Bash / ShellCheck | `bash -n` on 133 scripts, all-script error check and active-script warning check pass |
| Lua | 83 files parse; required shortcut/duplicate audit passes |
| `git diff --check`, `git diff --cached --check` | Pass |

The complete dependency/session commands were not made green by hiding their
failures. This WSL HOME lacks deployed Hyprixe configs (including the new Rofi
file), the system SDDM theme/greeter, several desktop executables and a live
Hyprland environment. The installed-file check adds one expected failure to the
previous environment totals. Native launcher tests used the separate correctly
deployed temporary user. Run the full commands on the physical PC after installing.

Changed existing files: `.config/hypr/scripts/RofiLauncher.sh`,
`scripts/build-runtime.sh`, `scripts/check-deps.py`, `scripts/rofi_compat.py`,
`scripts/verify.py`, `tests/test_runtime.py`, `README.md`, `INSTALL.md` and this
validation report. Added files: `.config/hypr/rofi/config-launcher.rasi`,
`.config/hypr/rofi/themes/Frosted-Glass-Launcher.rasi`, `scripts/rofi_launcher.py`,
`scripts/rofi_checks.py`, `tests/test_rofi_launcher.py` and `docs/ROFI.md`.
No tracked file was deleted and no commit was created.

Evidence outside Git: `/root/.cache/hyprixe-validation/rofi-launcher-build.log`,
`rofi-launcher-verify.log`, `rofi-launcher-dependencies.log`,
`rofi-launcher-session-verify.log`, `rofi-launcher-session.log` and the
`rofi-launcher-*.png` native screenshots. The build directory is
`/root/.cache/hyprixe-validation/rofi-launcher-source`.

Physical Hyprland 0.56.2 GPU blur, the final composited colours, real application
startup and physical keyboard/mouse interaction still require target-machine
validation. No compositor configuration or keybinding was changed.

## Rofi glass paint and wider wallpaper — 2026-10-28

This update changes the dedicated launcher paint and proportions. The shared
Rasi theme/palette/fonts, launch script, UWSM helpers, four button actions,
window switcher, keyboard bindings and Hyprland blur rules are unchanged.
No package, image copy, generated preview or new runtime dependency is added.

- Window width changes from 60% to 70% (**+16.7%**); height remains **58%**.
- Wallpaper width changes from 25% to 32% of output width, approximately
  **48% wallpaper / 52% applications** after padding on ordinary desktop outputs.
- Main paint is Rofi color2 `#284D5B` at alpha **0.82**, drawn once. Previously,
  the inherited black window/mainbox paints compounded 0.70 alpha to 0.91.
- Search/messages use color3 `#345461` at **0.40**; normal round buttons use the
  same RGB at **0.76**. Selection uses color11 `#457081` at **0.92** with light
  foreground text; hover uses color12 `#4D7A8A` at **0.92**. Borders reuse
  Waybar/Wlogout cyan `#7ED6FF` at **0.20**. Unselected rows and their child
  icon/text backgrounds are fully transparent, including alternate states.

The wider wallpaper exposed a real 32:9 image-repeat problem in stock Rofi
height scaling. The only additional renderer adaptation is activated by
`hyprixe-preview-cover: true` on the wallpaper box: if the height-scaled image
is too narrow, Rofi requests the width-scaled variant from its existing image
cache. Both paths preserve image aspect ratio. Other widgets/menus do not enable
the property, and launcher action handling is unchanged. A Rasi media-query
experiment was removed: upstream 2.0.0's Wayland `monitor_active()` is a no-op,
making its dimensional theme conditions unsuitable for this fallback.

The pinned Rofi build completed with `meson compile -C` after applying the
updated `scripts/rofi_launcher.py`. The first experimental build exposed that
upstream widget test binaries do not link `find_arg`; the final implementation
uses a local theme boolean instead and all build targets link successfully.
The capability probe distinguishes an older actions-only Rofi from one that
supports the new image rendering. `./install.sh native` prepares that build
automatically; `--no-packages` intentionally cannot upgrade an old binary.

Final results with the prepared runtime in PATH:

| Command / check | Actual result |
| --- | --- |
| `./verify.sh` | **218 tests OK**, exit 0, `RESULT: 0 failed check(s)` |
| `./verify.sh --dependencies` | 218 tests OK; 12 unchanged failures in the undeployed WSL environment |
| `./verify.sh --dependencies --session` | 218 tests OK; 16 unchanged environment/session failures in WSL |
| Rasi parsing | All eight files parse with real Wayland Rofi |
| Bash / ShellCheck / Lua | 133 scripts pass syntax, both ShellCheck levels pass; 83 Lua files and shortcut audit pass |
| Original asset hashes | Wallpaper and original Kvantum assets remain identical |
| `git diff --check`, `git diff --cached --check` | Pass |

An external temporary-user fixture deployed the files and used actual Rofi
Wayland, UWSM/systemd and headless Sway. Native virtual pointer/keyboard tests
passed immediate search, Enter/Escape, all four buttons and the existing switcher.
Applications stayed in one Rofi process, and ordinary dmenu retained custom-action
exit code 26. Application launches and Hyprland IPC used harmless stand-ins.
Screenshots were inspected at 1920×1080, 1366×768, 2560×1440 scale 2,
3440×1440 and 5120×1440 scale 2: no black row rectangles, translucent blue/grey
paint, light readable text, round buttons/corners and a continuous proportionate
wallpaper. The initial 32:9 repetition was corrected and rechecked.

The final binary was rebuilt after removing diagnostic-only image logging;
the rendering path is the same as in those native input/screenshot tests.
No physical Hyprland/GPU session was available: final blur strength, colour
integration against the real desktop and physical input remain manual checks.
The full dependency/session failures are reported, not suppressed or presented
as successful physical-PC runs.

Changed files: the dedicated `Frosted-Glass-Launcher.rasi`,
`scripts/rofi_launcher.py`, `scripts/rofi_compat.py`, `scripts/check-deps.py`,
`scripts/verify.py`, `tests/test_rofi_launcher.py`, `docs/ROFI.md`, `INSTALL.md`
and this report. No tracked file was deleted and no commit was created.
External evidence: `/root/.cache/hyprixe-validation/rofi-glass-build.log`,
`rofi-glass-verify.log`, `rofi-glass-dependencies.log`,
`rofi-glass-session-verify.log`, `rofi-glass-session.log` and
`rofi-glass-*.png` native screenshots.

## Shared Wlogout entrypoints — 2026-10-30

The active module list in `hypr/hyprland.lua` loads `lua/keybinds.lua`, followed
by the personal overrides. The shipped overrides contain no active bindings.
The audit found one legacy keyboard entrypoint: `SUPER + SHIFT + E` called
`PowerMenu.sh`, which displayed a Rofi list with Lock, Suspend, Logout, Reboot
and Shutdown. Waybar's power button also called that script. Historical
`CTRL + ALT + Delete` / `CTRL + ALT + P` bindings and Rofi/Wlogout scripts under
`extras/kooldots` are not sourced or deployed and remain reference material.

Both `SUPER + Backspace` and `SUPER + SHIFT + E` now execute `hyprixe-session`
directly. `PowerMenu.sh` is retained only as an `exec` relay for Waybar and
existing callers; the old Rofi list and its action/confirmation implementation
are removed. No standalone power/logout/session Rasi file was present in the
active tree. The shared `rofi/config.rasi` remains necessary for confirmations,
the window switcher and other menus. No theme asset or launcher file was removed.

The live audit requires keybind revision 2 and the Wlogout descriptions, so a
still-loaded older configuration is rejected until installation and reload.
The recording Lua load test checks both callback targets, preserves
`SUPER + Space` and rejects legacy menu scripts on loaded binds. Regressions
also cover duplicate/misdirected shortcuts, relay exit-status propagation,
installation/repeat/restore of the old script and original file modes.

Commands actually executed in Debian 13 WSL with the previously prepared
runtime binaries on PATH:

| Command/check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p test_wlogout.py -v` | 15 tests passed |
| `python3 -m unittest discover -s tests -p test_keybind_checks.py -v` | 17 tests passed |
| `python3 -m unittest discover -s tests -p test_runtime.py -v` | 28 tests passed |
| `./verify.sh` | 219 tests passed; `RESULT: 0 failed check(s)`; exit 0 |
| `./verify.sh --dependencies` | 219 tests passed; 12 installation/environment checks failed; exit 1 |
| `./verify.sh --dependencies --session` | 219 tests passed; 16 installation/environment/session checks failed; exit 1 |
| Real Hyprland 0.55.2 `--verify-config`, isolated unprivileged HOME | Passed, including all 68 retained binding handles and native dispatcher constructors |
| `hyprctl configerrors` in WSL | Unavailable: `HYPRLAND_INSTANCE_SIGNATURE not set!` |
| Isolated headless compositor/IPC attempt | Could not create a graphical backend; no live registry or physical key events validated |
| `git diff --check` and `git diff --cached --check` | Passed |

The 12/16 environment failures match the preceding WSL run: this HOME has no
deployed desktop/SDDM configuration, several graphical commands are absent,
and there is no active Hyprland/UWSM session. They were not suppressed. Logs
are outside the repository under `/root/.cache/hyprixe-validation/session-menu-*`.

The Rofi launcher, Wlogout layout/CSS/helper, Waybar configuration/CSS, layer
rules, UWSM units, profiles and other applications are unchanged. Normal
deployment backs up the replaced script and keybind file; the existing restore
transaction restores both. On the physical PC, close Dolphin, run
`./install.sh native --no-packages`, `hyprctl reload`, `hyprctl configerrors`
and `./verify.sh --dependencies --session`. Check both session shortcuts,
cross-shortcut toggle behavior, Waybar power and the unchanged Rofi launcher.
Hyprland 0.56.2 live IPC and physical input remain target-machine checks.
