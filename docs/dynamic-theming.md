# Dynamic Wallpaper Theming — v1.2.0 candidate

Hyprixe keeps its Frosted Glass layout, blur, opacity, rounding, spacing, fonts,
animations and menu actions. Only colour values change. This is dark-first,
including for a very bright wallpaper; there is no automatic light mode.

```bash
hyprixe-theme apply ~/Pictures/wallpaper.jpg
hyprixe-theme refresh     # Force extraction of the current wallpaper again
hyprixe-theme status
hyprixe-theme default     # Default wallpaper + colours; preserve enabled preference
hyprixe-theme disable     # Persist default colours across wallpaper changes
hyprixe-theme enable      # Enable and regenerate the current wallpaper
```

| Command | Persistent preference |
| --- | --- |
| `enable` | Set enabled, then regenerate |
| `disable` | Set disabled; retain selected image, generate Frosted Glass colours |
| `apply IMAGE` | Preserve enabled/disabled; select the image after a successful transaction |
| `refresh` | Preserve enabled/disabled and selected wallpaper; rebuild the cache |
| `default` | Preserve enabled/disabled; select min_forest.jpg and default colours |
| `status` | Read persistent preferences and report the separate cache state |

Only `enable` activates an existing preference. After `default`, a subsequent
apply/refresh/login uses dynamic colours if the saved preference is enabled;
use `disable` for a persistent default palette. Enable/disable record the
explicit choice before generation, so it survives a later rendering failure.
The installer's internal `init` enables a genuinely fresh installation once;
it preserves existing or migrated preferences on reinstall/recovery. Public
commands without any previous state start disabled until `enable` is requested.

Use `apply` as the canonical wallpaper command. The existing `Wallpaper.sh`
startup/hotplug helper delegates to `hyprixe-theme restore`; it retains the
existing awww daemon, output readiness checks and UWSM service lifecycle.
There was no active wallpaper selector to migrate (the KoolDots selector in
`extras/` is archival). No additional graphical manager or shortcut is added.

## Pipeline and ownership

`common/theme/` contains the engine, extraction configuration, raw JSON
template, semantic component templates and `defaults/frosted-glass.json`.

1. Validate the image with Pillow and calculate its SHA-256.
2. Extract raw colours with the pinned Wallust using a private configuration,
   `wallust run`, `--skip-sequences`, `--no-hooks` and `--no-cache`.
3. Map the extracted chroma to Hyprixe roles: background, surfaces, foreground,
   muted foreground, two accents, borders/focus, success/warning/error,
   selection and workspace accent. Components never map `color0`–`color15`.
4. Keep surfaces dark and saturation restrained. Check text contrast (4.5:1
   against the opaque semantic surfaces), selection contrast and visible
   accents/borders (3:1 against the base background). Translucent rendering
   still needs visual testing on the actual display.
5. Render and validate seven colour fragments in a private temporary directory.
6. Apply awww once, then atomically replace the `current` generation symlink.
   Reload active components through one orchestrator, then save the successful
   wallpaper selection atomically in XDG_STATE. No source configuration is
   rewritten at runtime.

Files live in `${XDG_CACHE_HOME:-~/.cache}/hyprixe/theme/generations/`.
`current/` points to one complete generation, including `palette.json`, metadata
and a manifest of SHA-256 hashes. This cache is entirely disposable.

`${XDG_STATE_HOME:-~/.local/state}/hyprixe/theme.json` is a **regular file**,
independent of the cache, containing only the format, enabled boolean, selected
wallpaper path and its last successful SHA-256. It is written to a temporary
file, fsynced, atomically renamed and followed by a directory fsync. Cache
metadata contains a regenerable state fingerprint to detect stale generations;
it never supplies preferences once the persistent file exists.

A single advisory `flock` in `XDG_STATE_HOME/hyprixe/theme.lock` serializes
transactions even if the entire cache directory disappears. Cache keys include image
bytes, engine/templates/defaults and enabled mode. Login validates the cached
generation, restores the wallpaper and avoids Wallust when unchanged. An
identical `apply` does not regenerate or reload colours; it reasserts the image
once in awww without a transition, including after an external wallpaper change.
`refresh` bypasses that cache. Removing `~/.cache/hyprixe` followed by `refresh`
rebuilds it with the saved image and preference. A missing/invalid saved image
produces a warning and uses the bundled wallpaper while retaining the saved
selection, last known hash and enabled/disabled preference for later recovery.

`status` reports enabled/disabled, current selected wallpaper/hash, cache
`valid`/`missing`/`invalid`, palette `dynamic`/`default` and Wallust version.
When valid, cached palette source and last generation time are also shown.
With no usable generated cache, palette is `unavailable` until regeneration;
status still shows the persistent selection/preference without creating cache.

Pre-release migration recognizes only the old Hyprixe `theme.json` and
`wallpaper` symlink targets. Readable legacy metadata preserves the preference
and selection even with corrupt colour fragments. Missing/ambiguous metadata
is migrated **disabled**, recovering the image path if possible. Only owned
legacy links are replaced/removed. If the old cache has already disappeared,
information which existed only there cannot be recovered. A corrupt new state
file fails with a clear error and is preserved for manual repair; login alone
uses a disabled/default recovery without overwriting the damaged state. The engine
never substitutes an enabled value from cache. Installation discovery of the
active awww image runs only on a genuine first initialization.

The bundled `min_forest.jpg` is calibrated by content hash to the original
Frosted Glass palette, including when copied or renamed. Installation discovers
the active awww image when possible; otherwise v1.1's bundled image is used.

## Colour refinement

Wallust 3.5.1 still extracts the image. Hyprixe then works in
[Oklab/Oklch](https://bottosson.github.io/posts/oklab/), using small standard-library
Python calculations. Lightness `L` is on a 0–1 scale; `C` is perceptual chroma,
not HSL saturation. Colours outside sRGB lose chroma at the same lightness/hue,
rather than being clipped into a different hue.

The primary accent ranks useful raw colours by bounded chroma and usable
lightness; near-white/black and dull browns receive less weight. Its hue stays
from the image, with `L` around 0.79–0.85 and requested `C` 0.09–0.13. A raw
alternative at least 36° away is preferred when its rendered colour is distinct
enough. Only monochrome/no-usable-alternative palettes derive a neighbouring
hue 54° away. Truly achromatic images use the historical cool accent hue.

| Role | Transformed palette |
| --- | --- |
| background / surface / surface_alt | `L` about 0.225 / 0.310 / 0.375 (±0.01); `C` ≤ 0.025; ordered dark levels with a subtle wallpaper tint |
| foreground / foreground_muted | `L` 0.94 / 0.80, `C` about 0.007 / 0.014; off-white and visible secondary text |
| border / border_focus | `L` about 0.54 / 0.63, `C` about 0.025 / 0.065; neutral inactive edge, restrained active edge |
| selection / workspace | Dark accent-tinted fills with bright text, rather than fluorescent blocks |
| success / warning / error | Stable green / amber / red hues from Frosted Glass; readable independently of the wallpaper |

Validation requires at least **4.5:1** for foreground and muted text on the three
opaque surfaces, foreground on selection/workspace/secondary fills, dark text
on bright accents, and accent/status text on surface_alt. Borders/focus must
reach **3:1** against background. Oklab distances must be ≥ 0.075 between
background/surface, ≥ 0.055 between surface/surface_alt, ≥ 0.075 between accents,
and ≥ 0.12 between foreground/muted. Surfaces have relative luminance
0.003–0.065; the separate Oklch lightness/chroma bounds prevent both neon and
washed-out accents. Checks run after RGB rounding.

Tests also composite the existing translucent Waybar, Rofi, Hyprlock input and
SDDM input layers over their brightest backdrop. These guarantees concern the
specified surfaces and controls, not arbitrary text directly over every possible
wallpaper pattern; blur/display rendering still needs visual review. Opacity,
layouts and blur are unchanged. Kitty and SDDM selections use dark text on a
bright accent. Waybar battery warnings/errors keep amber/red, and SwayNC critical
notifications keep a red border.

The **exact historical palette** remains the default/fallback and the
content-hash calibration for `min_forest.jpg`. Its existing general contrast
checks still apply; the new tonal/distance envelopes apply to transformed
palettes. No palette roles, manifest/state format or SDDM protocol change is
needed. The existing engine/template fingerprint invalidates older generated
colours on the next generation.

For an offline contact sheet and 13 tiny generated wallpapers, without changing
your selected theme or state:

```bash
python3 tests/preview_palette.py --wallust \
  --output /tmp/hyprixe-palette-preview.html \
  --png /tmp/hyprixe-palette-preview.png \
  --fixtures /tmp/hyprixe-palette-fixtures
```

Open the HTML report to inspect raw and semantic swatches. Omit `--wallust` to
isolate the Hyprixe transformation using controlled raw-palette fixtures. Very
uniform/pale images can legitimately contain too few colours for Wallust; the
report labels those as the existing Frosted Glass fallback. This development
tool adds no runtime command or dependency.

## Supported components

| Component | Integration |
| --- | --- |
| Hyprland | Generated Lua colours imported after fixed decoration defaults; active/inactive/group borders and shadow colour; one `hyprctl reload` |
| Waybar | CSS colour definitions imported by the existing static style; SIGUSR2 reload |
| Rofi | One generated Rasi palette through the former `wallust/colors-rofi.rasi` compatibility import and `Frosted-Glass-Common.rasi`; all three menus keep their layout/actions |
| Wlogout | Colour definitions; four horizontal Lock/Logout/Shutdown/Reboot actions and fixed SVG icons preserved |
| Kitty | Separate included colours; SIGUSR1 reload for running user processes with a registered handler, supported by Debian Trixie's Kitty 0.41.1; no terminal closure or remote-control access required |
| Hyprlock | Sourced colour variables and stable current wallpaper; positions, blur and PAM unchanged; updates on the next lock |
| SwayNC | Shared GTK colour definitions with paint selectors; default widgets/layout and notification behaviour preserved; `swaync-client --reload-css` |

Rofi and Wlogout read colours at their next launch. Existing locks are not
restarted. The Rofi wallpaper preview and Hyprlock background follow the same
current selection as the desktop, through the stable user data link.

Kitty's reload signal is documented in the
[0.41.1 upstream manual](https://github.com/kovidgoyal/kitty/blob/v0.41.1/docs/conf.rst).

Kvantum stays static: its SVG paint and application-specific Dolphin variant
have no small shared palette-variable interface. Global SVG substitution would
damage the carefully separated light/dark paint. Powerlevel10k's existing
explicit RGB prompt colours stay static; ANSI terminal colours do update in
Kitty. SDDM receives a separate system snapshot as described below.

## Current wallpaper and login screen

`theme.json` is the only authoritative wallpaper selection. The derived symlink
`${XDG_DATA_HOME:-~/.local/share}/hyprixe/current-wallpaper` points to a validated
image and is replaced atomically under the theme lock. Rofi's launcher preview
and Hyprlock use this stable path, including with spaces/custom XDG roots;
their main configurations are never rewritten when selecting another image.
Login/hotplug restores the saved selection through `hyprixe-theme restore`.
If its image is unavailable, the link and desktop use `min_forest.jpg`, with a
warning; saved path/hash/preferences remain available for recovery. Refresh or
restore reconstructs the link as needed. Keep selected source images available.

On Debian the installer enrolls the invoking user's numeric UID in root-owned
`/etc/hyprixe/sddm-sync-users.json` and installs a socket-activated receiver.
`hyprixe-login-theme-sync` is a platform hook invoked after a successful theme
transaction (also init/restore/refresh). It sends seven semantic colours and
an open read-only image descriptor over `/run/hyprixe-sddm-sync.sock`.
No sudo prompt, shell command, source path or destination path is sent to the
receiver. Other platforms can supply their own hook; the core contains no
Debian/systemd mechanism.

The receiver runs as the dedicated **non-login, unprivileged** `hyprixe-theme`
account with an isolated HOME, read-only system, no capabilities, private
network/devices and bounded memory. Linux `SO_PEERCRED` authenticates the caller;
only installer-enrolled UIDs may publish. The received descriptor must identify
a regular image owned by that UID (at most 32 MiB/36 megapixels, JPEG/PNG/WebP/BMP).
The receiver verifies bytes/hash and decodes/re-encodes RGB PNG, stripping
metadata. An image owned by another account can still work in the desktop, but
its SDDM export is refused with a warning; copy it into your own files first.
Paths/options/traversal are not part of the protocol. No sudoers rule is added.

`/var/lib/hyprixe/theme/generations/<id>/` contains readable `wallpaper.png`,
`palette.json`, data-only `Palette.qml` and checksums; `current` switches to a
complete generation atomically. Files use 0644, directories 0755 and belong to
the receiver account. No user HOME access or Wallust execution is required by
SDDM. The QML structure stays static and optionally loads the generated data;
absent/malformed colours or an unavailable copied image select the original
Frosted Glass wallpaper and paint. Several complete predecessors are retained;
failure before publication leaves the prior snapshot intact.

`apply`, `enable`, `disable`, `refresh`, `restore` and installation initialization
sync the resulting image/palette. `disable` exports the selected image with
default colours; `enable` exports that same image with calculated colours.
`default` exports **min_forest.jpg + default colours** for the next greeter.
Sync failure warns without undoing the working session; `hyprixe-theme refresh`
retries. No greeter/display-manager restart occurs. A greeter already open may
keep its loaded snapshot until its next launch.

Multi-user policy: **last successful sync from an installer-enrolled account
wins**. Accounts cannot modify the allowlist or another user's files. The image
is deliberately made public for the greeter; choose wallpapers accordingly.
Root-only installation changes require the existing sudo installer once.
Ordinary backup/restore covers the hook, system units/code, authorization and
SDDM configuration. Restore stops/removes the managed socket when reverting its
installation; inert snapshots and the non-login account are retained, as are
user theme state/cache. No global XDG directory or unrelated file is deleted.

The transport uses [systemd socket activation](https://www.freedesktop.org/software/systemd/man/latest/systemd.socket.html),
[Unix descriptor passing](https://docs.python.org/3/library/socket.html#socket.socket.recvmsg)
and an optional [Qt Loader](https://doc.qt.io/qt-6/qml-qtquick-loader.html).

## Wallust and Debian installation

The exact supported release is **3.5.1**, published 2026-01-16, non-yanked in
the registry. Only `raw.json` uses Wallust v3 MiniJinja syntax (`{{ color0 }}`);
the component templates use Hyprixe's own `@semantic_role@` substitutions.
Old v2 filters/methods and the archival v4 examples in `extras/` are not loaded.

Sources: [published release and source](https://docs.rs/crate/wallust/3.5.1),
[v3 migration](https://explosion-mental.codeberg.page/wallust/v3.html),
[template configuration](https://docs.rs/crate/wallust/3.5.1/source/docs/config/template.md).

Audit on 2026-11-03: the official
[Trixie main amd64 index](https://deb.debian.org/debian/dists/trixie/main/binary-amd64/Packages.xz)
and [Trixie backports main amd64 index](https://deb.debian.org/debian/dists/trixie-backports/main/binary-amd64/Packages.xz)
contain no `Package: wallust` entry. Hyprixe therefore does not assume an APT
package exists. The Debian profile downloads the immutable
[3.5.1 crate](https://static.crates.io/crates/wallust/wallust-3.5.1.crate), checks
SHA-256 `45afe16bc8c14dab61ff2acf885034664a6b917ca2ea874ff24eb5107d311ecc`
against the pinned registry checksum, safely extracts it and builds with
`cargo build --release --locked`. Cargo checks dependency archive hashes from
the published lockfile. No detached upstream signature is claimed.

Build tools/Rust come from official Debian packages/backports. Source and
dependencies are pinned; bit-identical binaries across changing compilers are
not promised. The binary is staged, then backed up/deployed with the existing
file transaction to `~/.local/bin/wallust`. A compatible installed version is
reused without downloading/building. Wrong major/minor versions are rejected.
Pillow and GTK introspection are Debian dependencies. Nothing downloads at login.

`./install.sh native --no-packages` checks Wallust **before creating temporary
files, preparing shell assets or deploying configuration**. Install normally
once to prepare a missing/incompatible Wallust. A scoped `--waybar-only` repair
without an initialized engine uses the default palette locally; run the full
installer to connect the desktop to dynamic theming.

For future NixOS, install Wallust 3.5.1 and Pillow/GTK, expose the same
`common/theme/` resources in the user data directory, resolve the import paths,
install the common entrypoint and initialize it. There is no APT/dpkg/systemd
policy in the engine. The NixOS profile remains unimplemented.

## Failure and recovery

An invalid requested image leaves the wallpaper and palette unchanged. Missing
Wallust, an unsupported version, insufficient image colours or extraction
failure use the original Frosted Glass colours. Parser/template rejection
keeps the previous good generation; without one, validated installation-time
fallback fragments are available. Output checksums detect corrupted files and
`refresh`/login repairs the generation. Failures are printed clearly to stderr
(the existing wallpaper service journal captures login errors).

Colour files are validated with constrained colour-only grammars, plus native
Rofi, Kitty, Lua and GTK parsers when available. Hyprland/Hyprlock fragments
have no independent native fragment validator; source grammar checks and live
Hyprland `configerrors` complement the parser tests. A failed compositor
activation restores the preceding generation and wallpaper. Soft reload issues
for disappearing Kitty/SwayNC processes are reported without closing apps.

`hyprctl configerrors` is normalized consistently in the engine and session
checks: blank/whitespace output and JSON arrays containing only blank strings
mean no errors. Real nonempty error messages still reject activation.

If state/wallpaper checks pass but cache validation fails, `status` now reports
whether the generation's state fingerprint differs from persistent state.
Pre-fix test fixtures could inherit the session's `XDG_CACHE_HOME` and replace
the real current generation with one belonging to a temporary test state. A
failed enable/disable reload can also leave an older generation selected after
rollback. Neither case justifies accepting mismatched fingerprints. Deployment
rendering and initialization now use the explicit target HOME/cache, and tests
isolate their cache. After updating installed files, regenerate from persistent
state without deleting preferences:

```bash
./install.sh native --no-packages
hyprixe-theme refresh
hyprixe-theme status
./verify.sh --dependencies --session
```

Installed import bridges, engine resources, fallback fragments and staged
Wallust use Hyprixe's ordinary file-level backups. Restore transactions in
reverse order with `./uninstall.sh`; user-edited files retain the existing
conflict protection. Mutable cache/state are intentionally outside deployment
manifests, so wallpaper changes do not block restoration. Restore retains both
the disposable cache and persistent preferences, as well as unrelated files;
this change adds no recursive uninstall cleanup or deletion of XDG roots.

## Validation

```bash
./verify.sh
python3 -m unittest discover -s tests -p 'test_dynamic_theme.py'
python3 -m unittest discover -s tests -p 'test_wallust_install.py'
python3 -m unittest discover -s tests -p 'test_wallpaper_propagation.py'
python3 -m unittest discover -s tests -p 'test_sddm_sync.py'
./verify.sh --dependencies --session  # inside the installed Debian desktop
```

Source tests generate six tiny blue/green/orange/purple/light/monochrome PNGs,
check semantic mapping/contrast, all component formats, real Wallust when
present, cache/hash invalidation, default/disable, corruption, atomic publication,
rollback, concurrency, archive integrity, `--no-packages` and Core ownership.
State regressions also cover disable plus corrupt CSS, complete cache deletion
in both modes, status without cache, corrupt JSON, legacy migration, missing
images, command preference contracts and failed atomic state commits.
The immutable v1 backup fixture still tests restore; explicit v1.2 import
changes are separated from the unchanged deployment contract.

On the physical PC, inspect all palettes over bright/dark images, all monitors,
Waybar continuity, open Kitty windows, notification actions, all three Rofi
menus and Wlogout; test login/hotplug, PAM unlock, disable/enable, reinstall and
reverse restore. WSL/source tests do not establish visual equivalence or a
working physical Hyprland/UWSM session.
