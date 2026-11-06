# Architecture

Hyprixe has one shared desktop Core and platform integrations. Debian 13 is
supported; NixOS is planned. Native/VMware are hardware choices within Debian,
not separate OS profiles. One Hyprixe release covers the whole repository.

```text
common/             desktop behaviour, theme engine, shell and shared assets
profiles/debian/    APT/build, deployment, system integration and platform adapters
profiles/nixos/     planned metadata only
scripts/            shared source mappings, verification and test runner
tests/              isolated Core/platform regressions and frozen fixtures
docs/wiki/          canonical documentation
docs/               screenshots, licenses and machine-readable audit evidence
```

> A shared Hyprixe component must have exactly one canonical source under `common/`. Profiles define platform integration, not duplicated desktop configuration.

## Ownership

| Core | Platform integration |
| --- | --- |
| Desktop layout, colours, bindings, runtime helpers | Package names and installation methods |
| UWSM lifecycle and shared user-service behaviour | Vendor service/authentication adapters |
| Wallpaper state, semantic palette and user-component imports | Debian SDDM receiver deployment and authorization |
| Shared greeter QML and fallback assets | System paths, backups and account-shell migration |

Edit shared behaviour once; do not copy it into profiles. Identical profile
copies and undeclared shadowing fail verification. Real platform divergence
needs an explicit declared integration/override.

## Deployment and session

`scripts/source_layout.py` maps canonical sources to installed HOME/XDG paths.
Kitty remains under `~/.config/kitty`; Rofi/Waybar under `~/.config/hypr`.
Configuration is copied transactionally, with original modes/symlinks, checksums,
XDG rendering and conflict protection. Backup manifest format 1 remains usable.

The shared session contract is:

```text
SDDM → Hyprland (uwsm-managed) → graphical-session.target → Hyprixe services
```

UWSM owns environment/application scopes; profiles implement the platform pieces.
The portable theme engine has no APT/dpkg policy. Debian alone provides the
optional authenticated SDDM sync transport. See [Dynamic Theming](Dynamic-Theming).

## Compatibility

The minimum is **Hyprland 0.55.2**, excluding prereleases of that minimum.
Reference release numbers are **0.55.2 and 0.56.2**. Other eligible versions get
a provisional warning, not an arbitrary upper-version rejection. Unrecognizable
versions or missing required APIs/configuration remain failures.

Version checks never replace parser, Lua binding/API, UWSM service or physical
acceptance checks. The source of this policy is `scripts/hyprland_version.py`.

## Contributing and evidence

Run `./verify.sh`, then installed/session checks on Debian where applicable.
The verifier separates Core and supported-profile regressions; planned profiles
are explicitly skipped. Frozen deployment/restore fixtures protect the original
Debian contract without duplicating the desktop configuration.

Machine-readable historical inventories remain under `docs/`; old narrative
audit/change/test logs remain available in Git history rather than current guides.
They are not proof that today's installed session passed. Preserve upstream
notices and review [assets](Assets) when changing bundled media.

Future NixOS integration should consume `common/` and reproduce the same session
contract. No working Flake, Home Manager module or rebuild command is provided yet.
