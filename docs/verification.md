# Verification

[Documentation index](README.md)

[verify.sh](../verify.sh) runs [scripts/verify.py](../scripts/verify.py), with
user-local executable precedence and bytecode generation disabled. It combines
repository checks, isolated tests and optional installed/live probes. It does
not install missing dependencies or repair the desktop automatically.

## Main modes

```bash
./verify.sh
./verify.sh --dependencies
./verify.sh --dependencies --session
```

| Mode | What it establishes |
| --- | --- |
| Default | Source structure/formats, Bash/Python/Lua checks when tools exist, paths/imports, native profile hygiene, original asset integrity and isolated deployment/runtime regressions |
| `--dependencies` | Also require installed executable capabilities, deployed component assets, SDDM/Qt integration, fonts, Zsh/plugins/prompt and account-shell consistency |
| `--session` | Query an existing Hyprland/UWSM session: config errors, version/API, loaded binding handles, services/environment, compositor blur and wallpaper IPC |

The isolated tests use temporary HOME/XDG paths and mocked commands where
appropriate. They test backup/restore, modes, failures, repeated deployment and
runtime logic without logging you out or powering off the machine. Passing
these tests is not equivalent to exercising a real graphical session.

## Additional options

```bash
./verify.sh --help
./verify.sh --sddm
./verify.sh --session --diagnostics
./verify.sh --waybar --session
./verify.sh --dolphin --session
```

- `--sddm`: add installed greeter/configuration and UWSM-entry checks without
  requiring the full `--dependencies` mode.
- `--diagnostics`: read-only login journals, service timing, client/layer and
  autostart diagnostics. Review output before sharing; titles and machine
  details can be personal. Use with `--session` for login-transition analysis.
- `--waybar`: scoped Waybar source/deployment/capability checks; optionally add
  `--session`. It does not run the complete project suite.
- `--dolphin`: scoped Dolphin source/deployed paint/Qt checks; optionally add
  `--session`. It does not run the complete project suite.

Scoped modes cannot be combined with each other, `--sddm` or `--diagnostics`.
Use the full mode for whole-project validation.

## Results and limits

`PASS` means that named check ran successfully. `FAIL` increments the failure
count and makes the command exit nonzero. A clean run ends with:

```text
RESULT: 0 failed check(s)
```

`SKIPPED` means a check did not run, often because optional tooling is missing,
no live probe was requested, or interactive hardware testing is required. It
is neither a successful visual test nor necessarily a problem. For example,
missing ShellCheck/Lua tooling can skip optional analysis. A missing required
runtime command under `--dependencies`, or requesting `--session` outside a
supported running session, is a real verification failure.

An installed incompatible X11-only Rofi or a Waybar lacking the needed IPC can
also be detected by default checks; default mode is not entirely independent
of available native tools. Component parsers use their real binaries where
possible and must not silently substitute another implementation.

No automatic check presses a physical shortcut, confirms a destructive action,
unlocks PAM, judges fonts visually, proves GPU blur quality or guarantees a
seamless SDDM transition. Test those on the PC after reconnecting. The
[release checklist](release-readiness.md) separates recorded automated evidence
from outstanding acceptance tests.

Historical counts and earlier limitations are in [VALIDATION.md](VALIDATION.md),
with dates. They are not a guarantee that your current installed session passed.
