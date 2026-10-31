# Core + Profiles validation

Scope: repository architecture only, on branch `refactor/core-profiles`.
Baseline: `0315699206f0450fdc79d92c0b622502abf17c95` (stable Debian checkout).
The existing release refs are unchanged; no commit, tag or release is created.

## Deployment contract

The [pre-move audit](core-profiles-audit.json) covers all 568 then-tracked files:
112 COMMON, 18 DEBIAN and 438 HISTORICAL / DOCS. FUTURE_NIXOS had no existing
implementation; only planned metadata/documentation has been added.

[Frozen fixtures](../tests/fixtures/README.md) were captured before moving
sources. Tests compare 16 native/VMware, default/custom-XDG and full/component/
runtime payloads: **736 target entries**, exact destination paths, normalized
SHA-256 and modes. Eight system greeter source hashes also match. Only temporary
HOME in text is normalized; binary wallpaper/theme/font bytes are unchanged.

A real old format-1 backup with synthetic originals is restored by the new
backend. Original 0600/0640/0664 modes, bytes and unrelated files are preserved.
Repeated installation over that populated v1 state is a no-op, with no new
backup. Existing regression suites cover symlinks, conflicts, failed writes,
rollback, linked SDDM transactions, shell changes and component-only installs.

Native profile defaults now have one source. Only two obsolete stubs that were
always replaced at deployment were removed. Zsh plugin tokens are rendered from
Debian metadata to the exact previous installed bytes. No desktop configuration,
wallpaper, theme geometry, colours, bindings or service behaviour is changed.

## Executed environment and checks

Windows workspace with Debian 13 WSL; no running physical Hyprland desktop.
Compatible prepared Rofi/Waybar/awww binaries and the verified shell/font stage
were supplied through PATH and `HYPRIXE_TEST_SHELL_STAGE`. Native tools include
Bash, ShellCheck, Lua, Kitty, Zsh, C++, Qt6 and PyQt6.

| Command/check | Result |
| --- | --- |
| `./verify.sh` | 0 failed checks; common and Debian regressions pass |
| `python3 -m unittest discover -s tests -v` | 254 tests pass with the prepared runtime/assets; no skips |
| `./verify.sh --profile nixos` | Core checks pass; planned integration explicitly skipped, no claim of NixOS deployment |
| `umask 0002; ./verify.sh` | 0 failed checks, including original-mode restoration |
| `./verify.sh --dependencies` | Source/regression checks pass; 13 installed-runtime failures in this unconfigured WSL HOME, identical failure categories to the baseline |
| `Hyprland --verify-config` through the isolated native probe as an unprivileged user | Pass: native parser, 68 retained handles and dispatcher constructors; no graphical session started |
| Bash / ShellCheck / Lua / Python | 135 Bash scripts, ShellCheck error/warning gates, 82 Lua files and Python AST pass |
| Rasi / QML / Qt / Kitty / Zsh | Native parsing and existing isolated runtime/model/startup tests pass; no physical rendering claim |
| Local Markdown targets | 220 local links resolve, including Wiki extensionless page links |
| `git diff --check`, `git diff --cached --check` | Pass |

The 13 dependency failures are missing deployment, services, greeter/packages,
fonts/account state and Dolphin's unconfigured Qt style in WSL. They already
exist before this refactor. No dependencies or machine state were fabricated to
make installed checks pass. `--dependencies --session` cannot be accepted here:
there is no active Hyprland/UWSM session or physical display to inspect.

## Debian PC acceptance

After reviewing and merging the branch, close Dolphin and run the unchanged
workflow from the checkout:

```bash
git pull --ff-only
./install.sh native
./verify.sh
./verify.sh --dependencies
./verify.sh --dependencies --session
hyprctl configerrors
```

Run `./install.sh native` again and confirm no managed-file transaction is
needed when nothing changed. Check SDDM's **Hyprland (uwsm-managed)** login,
Waybar and wallpaper services, Rofi, Wlogout, Kitty/Zsh/P10k, Dolphin, lock,
clipboard, screenshots, window cycling and four persistent workspaces.
The expected desktop is the same v1 desktop; no new visual acceptance target
was introduced. Review the backup list and perform a restore in a disposable
account if physical restoration acceptance is required.

NixOS still needs actual declarative platform integration, packages/path
resolution and native installation/session validation. Planned status does not
count as a supported release target.
