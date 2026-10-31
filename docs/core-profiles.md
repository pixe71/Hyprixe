# Core and platform profiles

The pre-move audit is recorded in [core-profiles-audit.json](core-profiles-audit.json).
It classifies the existing files against the stable Debian baseline before any
source relocation. Debian's installed layout and public commands remain the
compatibility contract; repository paths are implementation details.

> A shared Hyprixe component must have exactly one canonical source under `common/`. Profiles define platform integration, not duplicated desktop configuration.

## Classification

| Category | Responsibility |
| --- | --- |
| COMMON | Desktop configuration, theme/lock/greeter assets, UWSM lifecycle/service behaviour, runtime helpers, hardware variants and pinned compatibility assets |
| DEBIAN | APT/backports/package names, mutable user/system deployment, SDDM system configuration, login-shell migration and Debian-specific adapters |
| FUTURE_NIXOS | Planned metadata and design notes only; no working Nix modules, flake or installer |
| HISTORICAL / DOCS | Versioned guides, release evidence, original inventories and optional examples; regression tests retain their core/platform classifications |

UWSM is a Core behaviour, not a Debian-only feature. Platform integration must
preserve SDDM -> Hyprland (uwsm-managed) -> graphical-session.target -> Hyprixe
services. The shared greeter is distinct from Debian's privileged installation
method. User-unit behaviour is shared; a vendor command using `/usr/bin` and
the distribution authentication-agent adapter belong to Debian.

## Installed-path compatibility

Common configuration is mapped to user destinations by one central layout
module. Kitty remains under `~/.config/kitty`; the v1 Rofi/Waybar destinations
remain under `~/.config/hypr`. This refactor does not perform a second runtime
path migration. Native/vmware are hardware choices, separate from OS profiles.

Debian plugin paths in Zsh are platform-rendered while the prompt/startup logic
has one shared source. Existing native-profile stubs that were always replaced
at installation are consolidated into the actual native defaults.

## Release and contribution policy

One repository release/version covers the Core and every platform; OS release
numbers in metadata are compatibility information, not separate Hyprixe versions.
Supported profiles must pass their required checks. Planned profiles are
reported as unimplemented and do not block release validation of supported ones.
They must not be advertised as installed or tested.

Edit shared components once under `common/`. A real platform divergence may
use an explicit integration/override; an identical copy is not an override.
The verifier checks for accidental common-source copies in profile directories.

The stable Debian deployment is captured before the refactor as hashes/modes
for native/vmware, default/custom XDG roots and full/component/runtime payloads.
A recorded format-1 backup exercises compatibility with the old restore data.
These fixtures are metadata, not duplicate desktop configurations.

See [architecture](architecture.md) for the concrete mappings and boundaries,
and [validation evidence](core-profiles-validation.md) for executed checks and
the remaining physical Debian acceptance steps.
