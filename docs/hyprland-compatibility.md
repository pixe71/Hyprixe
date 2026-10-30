# Hyprland version policy

[Documentation index](README.md)

The installer dependency preflight and live binding verifier share
[scripts/hyprland_version.py](../scripts/hyprland_version.py). There is one
eligibility rule, with no independent live-version whitelist.

| Category | Policy |
| --- | --- |
| Below 0.55.2, or a prerelease of that minimum | Rejected: Hyprixe requires the 0.55.2 Lua API |
| 0.55.2 and 0.56.2 | Reference release numbers examined against upstream API/source; not a blanket certification of all binaries or hardware |
| Other releases/builds at or above the minimum | Eligible, with an explicit provisional/unreviewed warning; no speculative upper bound |
| Failed/unrecognizable version query | Failure: the executable/version cannot be established |

The reference evidence includes a native 0.55.2 parser in the development
environment, upstream 0.56.2 source/API review, and the user's report of a
working 0.56.2 installation. It does not establish a fresh physical acceptance
run for this release candidate. Debian repacking of a reference number does
not imply that every downstream patch was separately reviewed.

For example, 0.56.3, 0.57.0 or a future 1.0.0 are not rejected solely for being
new. They are **not advertised as officially validated**. Development/RC
builds also remain provisional. No additional incompatibility interval is
currently recorded; a future exclusion needs an actual technical reason and
regression coverage.

## Capability checks remain mandatory

Version eligibility does not bypass configuration parsing, required bindings,
Lua handle/window-query/dispatcher checks, UWSM services or dependency checks.
The live verifier reports an actual missing API or configuration error as a
failure on any version. Its API probe constructs dispatchers and executes only
`no_op`; it does not test power actions or manipulate user windows.

```bash
hyprctl version
hyprctl configerrors
./verify.sh --dependencies --session
```

Passing these checks on an unreviewed release is useful compatibility evidence,
not automatic certification. Complete the physical checklist in
[release readiness](release-readiness.md) and record exact versions/results
before expanding the reference set. Warnings do not increase the failed-check
count; genuine capability/configuration errors do.

Regression tests cover reference, older, malformed, failed-query, packaged,
prerelease and future version outputs, agreement with the real installer
preflight, and future live versions whose API succeeds or fails.
