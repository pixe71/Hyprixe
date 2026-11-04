# Dynamic Wallpaper Theming — v1.2.0 candidate

Hyprixe keeps its Frosted Glass layout, blur, opacity, rounding, spacing, fonts,
animations and menu actions. Only colour values change. This is dark-first,
including for a very bright wallpaper; there is no automatic light mode.

```bash
hyprixe-theme apply ~/Pictures/wallpaper.jpg
hyprixe-theme refresh     # Force extraction of the current wallpaper again
hyprixe-theme status
hyprixe-theme default     # Default colours now; preserve the enabled preference
hyprixe-theme disable     # Persist default colours across wallpaper changes
hyprixe-theme enable      # Enable and regenerate the current wallpaper
```

| Command | Persistent preference |
| --- | --- |
| `enable` | Set enabled, then regenerate |
| `disable` | Set disabled, then generate Frosted Glass defaults |
| `apply IMAGE` | Preserve enabled/disabled; select the image after a successful transaction |
| `refresh` | Preserve enabled/disabled and selected wallpaper; rebuild the cache |
| `default` | Preserve enabled/disabled; use default colours for this generation |
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
identical `apply` does not rewrite, recolour, reload or transition again.
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
file fails with a clear error and is preserved for manual repair; the engine
never substitutes an enabled value from cache. Installation discovery of the
active awww image runs only on a genuine first initialization.

The bundled `min_forest.jpg` is calibrated by content hash to the original
Frosted Glass palette, including when copied or renamed. Installation discovers
the active awww image when possible; otherwise v1.1's bundled image is used.

## Supported components

| Component | Integration |
| --- | --- |
| Hyprland | Generated Lua colours imported after fixed decoration defaults; active/inactive/group borders and shadow colour; one `hyprctl reload` |
| Waybar | CSS colour definitions imported by the existing static style; SIGUSR2 reload |
| Rofi | One generated Rasi palette through the former `wallust/colors-rofi.rasi` compatibility import and `Frosted-Glass-Common.rasi`; all three menus keep their layout/actions |
| Wlogout | Colour definitions; four horizontal Lock/Logout/Shutdown/Reboot actions and fixed SVG icons preserved |
| Kitty | Separate included colours; SIGUSR1 reload for running user processes with a registered handler, supported by Debian Trixie's Kitty 0.41.1; no terminal closure or remote-control access required |
| Hyprlock | Sourced colour variables; background image, positions, blur and PAM unchanged; new colours on the next lock |
| SwayNC | Shared GTK colour definitions with paint selectors; default widgets/layout and notification behaviour preserved; `swaync-client --reload-css` |

Rofi and Wlogout read colours at their next launch. Existing locks are not
restarted. The Rofi wallpaper preview and Hyprlock background remain the bundled
image in this first implementation; the desktop wallpaper itself changes.

Kitty's reload signal is documented in the
[0.41.1 upstream manual](https://github.com/kovidgoyal/kitty/blob/v0.41.1/docs/conf.rst).

Kvantum stays static: its SVG paint and application-specific Dolphin variant
have no small shared palette-variable interface. Global SVG substitution would
damage the carefully separated light/dark paint. Powerlevel10k's existing
explicit RGB prompt colours stay static; ANSI terminal colours do update in
Kitty. SDDM stays static because it runs outside the user session.

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
