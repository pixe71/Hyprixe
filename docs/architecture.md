# Architecture

[Documentation index](README.md)

## Source and deployment

```text
hyprixe-debian/
├── .config/          user configuration, Lua modules, scripts and user units
├── .local/share/     KDE assets, colours and the Waybar logo font
├── .zshrc            interactive shell startup (not a system-script interpreter)
├── .p10k.zsh         supplied prompt configuration
├── wallpapers/       original min_forest.jpg
├── profiles/         native and opt-in VMware overlays
├── sddm/             own Qt6 greeter source
├── scripts/          deployment, assets, checks and session diagnostics
├── tools/            maintainer generators / compatibility patches
├── tests/            isolated deployment and runtime regression tests
├── extras/           optional inherited examples, not loaded by default
├── docs/             canonical reference, history and future Wiki gateways
├── packages*.txt     Debian runtime/scoped/optional package lists
├── install.sh        public installer entrypoint
├── uninstall.sh      public restore entrypoint
└── verify.sh         public validation entrypoint
```

The checkout is not symlinked wholesale over HOME. Bash entrypoints orchestrate
Python helpers that construct file payloads, render XDG placeholders and apply
individual files transactionally. File-level backups and hashes protect
existing configuration. Custom roots must remain within HOME; symlinked parent
directories are refused. See [deployment](../scripts/deploy.py).

## Compositor load graph

[hyprland.lua](../.config/hypr/hyprland.lua) explicitly loads defaults,
environment/profile, settings, decorations, animations, monitor/workspace and
window/layer rules, then keybindings and startup. User overrides are explicit,
including a binding override after the main bindings. An old `hyprland.conf`
is backed up/removed during full deployment so it cannot silently supersede
the Lua entrypoint.

The native profile does not require software graphics overrides or a specific
output name. The optional VMware overlay keeps those adaptations separate.
`extras/` is an example library, not an implicit autoload directory.

## Session ownership

SDDM selects Debian's existing UWSM desktop entry. UWSM starts Hyprland and
owns `graphical-session.target`. Hyprland's startup helper finalizes the
environment and queues `hyprixe-session.target`. Wallpaper/daemon, Waybar,
SwayNC, Hypridle, clipboard watchers and Polkit are session-owned user services.
Vendor dependencies are retained through focused drop-ins. See [UWSM](uwsm.md).

Application helpers consistently launch graphical applications through UWSM
where appropriate. Menu pipelines that need captured stdout preserve that
contract. Wlogout's named transient service implements toggling; fixed action
dispatch and confirmation are separate from its visual layout.

## Dependency and asset preparation

[build-runtime.sh](../scripts/build-runtime.sh) checks capabilities before
preparing pinned fallback builds. Current source pins are awww v0.12.1,
Waybar 0.12 and Rofi 2.0.0; full commits and patches are in the script/tools.
Waybar needs Lua workspace IPC, native taskbar and click-to-reveal drawer.
Rofi needs Wayland, the scoped sidebar actions and adaptive wallpaper cropping.

[apt-build-deps.py](../scripts/apt-build-deps.py) matches development packages
to installed backported source families, including transitive headers. It
does not force the entire system to backports or request library downgrades.

[shell-sources.json](../scripts/shell-sources.json) pins Powerlevel10k and the
symbol font; [shell_assets.py](../scripts/shell_assets.py) verifies archives,
gitstatus, file hashes and modes before staging. Installed asset sets or caches
can be reused offline. Generated assets are not committed to the source tree.

## Privileged changes and restoration

APT and SDDM system files require sudo; user files remain owned by the invoking
account. SDDM has a private system transaction linked to the full user backup.
The account-shell migration occurs last after quiet native Zsh checks and is
recorded for restoration. Package transactions and the added APT source are
not rolled back by the user-file uninstaller.

The restorer validates original backup integrity and current targets before
writing. Component-specific merges preserve unrelated Dolphin interface and
KDE/MIME/Qt settings where explicitly implemented, rather than promising
arbitrary merging for all files.

## Verification and documentation

The portable verifier runs syntax, formats, imports, paths, asset integrity and
isolated tests. Optional native parsers and dependency probes add evidence;
`--session` checks real loaded state without executing power/lock actions.
Physical rendering and input acceptance remain separate manual work.

`docs/` is canonical and versioned with the code. Wiki pages are lightweight
links to it. Historical audits retain earlier facts rather than being presented
as current configuration. No release or tag is generated by documentation work.
