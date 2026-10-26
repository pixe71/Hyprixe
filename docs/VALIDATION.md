# Validation performed

Audit dated October 25, 2026 (Europe/Paris), from Windows with Debian 13 under
WSL2, x86_64. **No Hyprland session on physical hardware was started.**
Interactive graphical commands are not presented as tested.

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
