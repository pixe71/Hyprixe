# Dynamic Wallpaper Theming

Hyprixe adapts its colours while keeping its dark Frosted Glass style.
Layouts, blur, opacity, fonts, animations and shortcuts stay unchanged.

```text
Wallpaper → Wallust → Hyprixe semantic palette
                              ↓
Hyprland / Waybar / Rofi / Wlogout / Kitty / Hyprlock / SwayNC / SDDM
```

## Commands

```bash
hyprixe-theme apply "$HOME/Pictures/my wallpaper.jpg"
hyprixe-theme refresh
hyprixe-theme status
hyprixe-theme enable
hyprixe-theme disable
hyprixe-theme default
```

| Command | Behaviour |
| --- | --- |
| `apply IMAGE` | Select the image; preserve enabled/disabled preference |
| `refresh` | Rebuild colours for the current image; preserve preference |
| `status` | Show preference, selected image/hash, cache validity and palette source/version |
| `enable` | Enable dynamic colours for the current image |
| `disable` | Use default colours but keep the selected image |
| `default` | Select `min_forest.jpg` and default colours; preserve preference |

Only `enable` activates an existing preference. After `default`, the next
apply/refresh/login uses dynamic colours if still enabled; use `disable` to
keep default colours. A fresh installation enables the feature once. Reinstall
preserves preferences; public commands without prior state start disabled.

## Colour identity

Wallust extracts raw colours; Hyprixe derives shared semantic roles:

- Three dark neutral surfaces with a subtle wallpaper tint.
- Readable off-white/secondary text and restrained borders.
- A controlled accent from the image and a distinct alternative; monochrome
  images can use a neighbouring hue, and grayscale uses the historical cool hue.
- Dark selected/workspace fills; recognizable green/amber/red status colours.

[Oklab/Oklch](https://bottosson.github.io/posts/oklab/) controls lightness, chroma
and separation. Transformed surfaces have relative luminance 0.003–0.065 and
chroma ≤0.025; accents use lightness about 0.79–0.85 and requested chroma 0.09–0.13.
Minimum Oklab distances are 0.075 between background/surface and accents,
0.055 between surfaces, and 0.12 between foreground/muted text.
Checks require **4.5:1** for the specified text/surface and selection pairs,
and **3:1** for borders against background. Transparency still needs visual review.

`min_forest.jpg` keeps the exact historical palette, including copies/renames.
It is also the default/fallback; the new tonal/distance limits apply to transformed
palettes. Kvantum and Powerlevel10k prompt colours remain intentionally static.

## Wallpaper and persistence

The current image reaches awww, the Rofi launcher, Hyprlock and the next SDDM
greeter. Rofi/Wlogout read new colours when opened; Hyprlock updates at the next
lock. Running components reload centrally without closing terminals.

| Location | Purpose |
| --- | --- |
| `$XDG_STATE_HOME/hyprixe/theme.json` | Persistent enabled preference, wallpaper path and hash |
| `$XDG_CACHE_HOME/hyprixe/theme/current/` | Disposable palette and component fragments |
| `$XDG_DATA_HOME/hyprixe/current-wallpaper` | Derived stable link for user components |
| `/var/lib/hyprixe/theme/current/` | Separate Debian SDDM wallpaper/palette snapshot |

Unset XDG roots default to `~/.local/state`, `~/.cache` and `~/.local/share`.
Keep the source image available. Login restores saved wallpaper/colours and
avoids extraction when the validated cache is unchanged. Deleting the cache
keeps preferences; `refresh` reconstructs it. Generation is locked, validated
and published atomically, without rewriting repository files.

## SDDM and fallback

SDDM reads a system copy, not your HOME. An unprivileged Debian receiver accepts
validated images/palettes only from installer-enrolled users, with kernel UID
authentication and fixed destinations. No permissive sudoers rule is installed.
Exported images must belong to the user and are made public for the greeter.
With multiple accounts, **the last successful authorized sync wins**.

Theme operations and login restoration synchronize that copy. `disable` exports
the current image with default colours; `default` exports the default image and
colours too. Sync failure warns without undoing the session theme; `refresh`
retries. An already-open greeter may retain its snapshot until its next launch.
Missing/invalid system data falls back to the bundled theme without blocking login.

An invalid requested image keeps the preceding theme. Failed extraction uses
Frosted Glass colours. Invalid output keeps a previous valid generation or the
installation-time fallback. Missing saved images use `min_forest.jpg` while
preserving preferences; corrupt state is preserved for diagnosis and never
silently enables the feature. See [Troubleshooting](Troubleshooting#dynamic-theming).

## Wallust and preview

Debian installs **Wallust 3.5.1** from a pinned
[source archive](https://static.crates.io/crates/wallust/wallust-3.5.1.crate),
checks SHA-256 below, and builds with `cargo build --release --locked`:

```text
45afe16bc8c14dab61ff2acf885034664a6b917ca2ea874ff24eb5107d311ecc
```

The Trixie/backports main amd64 audit on 2026-11-03 found no Wallust package.
Compatible installations are reused; nothing downloads at login.
`--no-packages` requires the pinned version before deployment.

For an offline colour report and tiny synthetic wallpapers, without changing state:

```bash
python3 tests/preview_palette.py --wallust \
  --output /tmp/hyprixe-palette-preview.html \
  --fixtures /tmp/hyprixe-palette-fixtures
```

Omit `--wallust` to isolate the transformation. Uniform/pale images may contain
insufficient colours; the report identifies the resulting safe fallback.
