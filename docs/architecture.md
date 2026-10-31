# Architecture

[Documentation index](README.md) · [Core/profile audit and contribution policy](core-profiles.md)

Hyprixe has one shared desktop Core and platform integrations. Debian 13 is
supported; NixOS is planned and has no working installer or Nix configuration.
One Hyprixe release covers the Core and its compatibility matrix.

```text
common/
  config/           desktop configuration and shared user-unit behaviour
  local/            session action helper, KDE assets and logo font
  shell/            Zsh template and Powerlevel10k prompt
  wallpapers/       desktop/lock/greeter image source
  sddm/             shared Qt 6 greeter visuals
  hardware/vmware/  optional graphics/monitor adaptations
  compat/           shared Rofi/Waybar capability probes and patches
  assets/           pinned shell/font source metadata
  tools/            verified shell-asset preparation
  metadata/dolphin/ interface recovery baseline
profiles/
  debian/
    profile.json    supported platform metadata and test groups
    packages/       APT package lists
    config/         Debian authentication-agent and vendor-unit adapters
    install/        APT/build, transactional deployment, SDDM and shell integration
  nixos/            planned metadata and design notes only
scripts/            shared source mappings, checks and test runner
tests/             common/platform regressions and frozen v1 deployment fixtures
docs/              canonical guides, historical evidence and small Wiki gateways
install.sh          compatibility entrypoint for Debian installation
uninstall.sh        compatibility entrypoint for Debian restoration
verify.sh           source, dependency and live-session entrypoint
```

## Canonical sources and deployment

> A shared Hyprixe component must have exactly one canonical source under `common/`. Profiles define platform integration, not duplicated desktop configuration.

Change a shared theme or binding once under `common/`; future platforms must
consume it directly. Identical copies in profiles fail verification. Real
divergences require declared overrides in profile metadata. There are currently
no overrides: the two Debian adapters add files rather than shadowing Core ones.

[source_layout.py](../scripts/source_layout.py) defines a small mapping from
canonical source prefixes to HOME/config/data destinations. It also resolves
v1 logical asset names used by historical inventories. It does not create a
second configuration tree. Debian consumes these mappings in its
[deployment backend](../profiles/debian/install/deploy.py).

The installed layout stays unchanged: `common/config/kitty` becomes
`~/.config/kitty`, and Rofi/Waybar remain under `~/.config/hypr/`. These explicit
runtime paths are independent of repository organization. Native/VMware are
hardware choices, not platform profiles. The native defaults have one source;
the unused stubs previously overwritten during installation were removed.

Zsh plugin paths are tokens in the shared template, rendered from Debian
metadata. The rendered `.zshrc` is byte-identical to the v1 deployment. Bash
scripts retain their shebangs. No desktop appearance or bindings change.

## Session contract

The shared contract is SDDM → **Hyprland (uwsm-managed)** →
`graphical-session.target` → Hyprixe user services. UWSM belongs to the Core.
Wallpaper/awww ordering, Waybar, SwayNC, idle, clipboard and Polkit lifecycle
remain unchanged. Platform profiles provide packages, vendor integration and
declarations implementing that contract; they must not duplicate its behaviour.

Debian's `/usr/bin/hypridle` drop-in and authentication-agent lookup are platform
adapters. Shared custom units and the other focused drop-ins remain in Core.
See [UWSM](uwsm.md) for the existing service lifecycle.

## Transactions and compatibility

Root Bash wrappers preserve the public commands and delegate to Debian's
backend. File-level payloads are copied transactionally, with XDG rendering,
hash/conflict checks, original permissions and rollback. User roots stay below
HOME and symlinked parents are refused. Existing Dolphin layout is preserved.

SDDM's visual source is shared; its privileged system deployment and separate
linked backup are Debian integration. The account-shell change remains last.
APT packages and backports sources are not rolled back by the user restorer.

Backup manifest format **1** is unchanged. Its absolute target paths and saved
bytes do not depend on repository source paths. A frozen pre-refactor backup
is restored in tests without migration. New installations retain the same
backup locations and conflict handling.

## Verification and future platforms

Metadata distinguishes `supported` and `planned`. Full verification runs common
regressions and every supported platform's required group; any failed group
fails validation. Planned profiles do not claim deployment support or block it.
Live session checks remain an explicit additional step. See
[verification](verification.md).

[Frozen fixtures](../tests/fixtures/README.md) compare 16 deployment cases
against commit `0315699206f0450fdc79d92c0b622502abf17c95`: native/VMware,
default/custom XDG roots and full/Waybar/Dolphin/runtime payloads. SHA-256,
destinations and modes are compared; SDDM sources are compared separately.

The NixOS implementation will study Flakes and Home Manager, consume `common/`
and reproduce the session contract. A future workflow might use
`sudo nixos-rebuild switch --flake ...`; **that command is not implemented by
this repository yet**. See [planned profile](../profiles/nixos/README.md).
