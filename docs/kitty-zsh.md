# Kitty, Zsh and Powerlevel10k

[Documentation index](README.md)

Hyprixe uses **Kitty** as its terminal, **Zsh** as the account's interactive/login
shell and **Powerlevel10k** as its prompt. All existing Hyprixe scripts continue
to run with their Bash shebangs. Bash stays installed; `.bashrc`, `.profile`,
`.bash_aliases` and Bash history are not modified or sourced as Zsh code.
There is no plugin manager or Oh My Zsh installation.

## Kitty appearance and launch

`SUPER + Return`, `TERMINAL`, the KoolDots defaults, Rofi terminal applications
and KDE's external-terminal action all use Kitty. The existing
`LaunchTerminal.sh` helper runs `uwsm app -- kitty "$@"`; there is no terminal
autostart or extra terminal daemon.

[kitty.conf](../.config/kitty/kitty.conf) uses background `#122434`, foreground
`#e6f1f4`, cyan selection `#7ed6ff` and pale cyan links. Background opacity is
0.92, with 12 pt JetBrains Mono and 10 px padding. Existing compositor opacity,
blur and rounding also affect the window. No graphics override is required by
the native profile.

Kitty's normal selection, links, tabs, splits and keyboard mappings are retained:
copy/paste is `CTRL + SHIFT + C` / `CTRL + SHIFT + V`, scrollback is 10,000 lines.
There are no custom Kitty mappings. Its configuration does not force `shell zsh`;
the account's default shell remains the authority.

## Versions and installation

Debian 13 supplies `zsh`, `zsh-autosuggestions` and `zsh-syntax-highlighting`.
The native validation used Zsh **5.9**, package `5.9-8+b24`, autosuggestions
`0.7.1-1` and syntax-highlighting `0.8.0-2`. APT chooses the official current
Debian candidates rather than pinning those package revisions or compiling Zsh.

Powerlevel10k comes from the official **romkatv/powerlevel10k v1.20.0** tag,
commit **`ff0311157d6b24fea21aa70699783f362b0f554f`**. The upstream commit archive
is pinned with SHA256
`cbd5ff7eed4bfa8805f1b1977255b2dfe0aac574b9758ae1a17e99fc135a77d8`.
`scripts/shell-sources.json` records every upstream URL, version and SHA256.
No checkout of `master`, remote shell evaluation or installation of Debian's
Powerlevel9k theme is involved. The upstream `POWERLEVEL9K_*` configuration API
and compatibility filenames are normal parts of Powerlevel10k.

`scripts/shell_assets.py` stages the exact verified files before deployment.
The matching official gitstatus daemon is downloaded during installation from
`romkatv/gitstatus`, using the version and checksum embedded in that pinned
Powerlevel10k archive. Linux x86_64 and aarch64 use **gitstatus v1.5.4**. Unsupported
architectures fail before changing the account; there is no implicit source build
or fallback mirror. HTTPS and SHA256 are checked for every download.

The installed theme is at:

```text
${XDG_DATA_HOME:-$HOME/.local/share}/hyprixe/powerlevel10k/
```

Its integrity manifest records the source commit, architecture, file hashes and
modes. A verified installation is reused without downloading/cloning again.
Download caches live under `${XDG_CACHE_HOME:-$HOME/.cache}/hyprixe/shell-sources`.
`--no-packages` prepares shell assets offline from that cache or the verified
installed files, and fails clearly if the initial dependencies/assets are missing.
Use the ordinary installer for the first migration:

```bash
cd ~/hyprixe-debian
git pull --ff-only
# Close Dolphin/configuration editors before the existing full deployment.
./install.sh native
```

The installer validates the real executable returned by `command -v zsh`, checks
it against `/etc/shells`, and verifies the invoking non-root account and its HOME.
It displays the old and intended shell. It then deploys/backups the files and SDDM,
refreshes the symbol font cache, tests gitstatus and runs silent `zsh -lic`
initialization. **Only after those steps succeed**, it runs:

```text
sudo /usr/bin/chsh -s VERIFIED_ZSH_PATH INVOKING_ACCOUNT
```

The actual system `chsh` path is discovered in Debian's system executable
directories. The username comes from the invoking UID's password-database entry,
not `$USER`, `root` or a hardcoded username. Its result is checked against that
database. A failure restores the previous transaction and any shell change.
Component-only Waybar/Dolphin installs and dry runs do not change the shell.

## Prompt and startup

The managed `~/.zshrc` starts with upstream's Instant Prompt preamble. It then
sets the local executable path and persistent history, initializes native Zsh
completion, loads `~/.p10k.zsh` and Powerlevel10k, loads Debian autosuggestions,
and sources syntax-highlighting last. It does not print banners, fetch plugins,
ask questions or run a configuration wizard during initialization. Instant
Prompt stays in `verbose` mode so actual startup output is not hidden.
The silent `GITSTATUS_AUTO_INSTALL=0` assignment before the preamble prevents
upstream daemon downloads even while a cached Instant Prompt is initializing.

The supplied prompt uses the existing Kitty/Frosted Glass cyan, pale blue and
grey-blue palette on a transparent prompt background. It shows the Debian icon,
context, directory, Git branch/state and a second input line. Exit errors,
commands lasting at least three seconds and an active Python virtual environment
appear only when relevant. Git includes dirty/staged/untracked information and
has no segment outside repositories. No Docker/Nix segments or aliases are added.

History is independent from Bash history and lives at:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe/zsh/history
```

It keeps 50,000 entries, shares history between terminals, removes duplicate
entries and ignores commands prefixed with a space. Up/Down search matching
history prefixes; Ctrl+R retains native incremental search. TAB uses native
completion with menu selection. The completion dump is under the XDG cache,
separate from history. Personal `.zshenv`/`.zprofile` files are preserved; an
incompatible `ZDOTDIR` or startup output is diagnosed before `chsh`.

## Kitty and glyphs

Kitty has no `shell zsh` override: its normal account-shell selection remains
in effect. Reconnect the entire desktop session after `chsh`, so Kitty/UWSM
inherit the new `SHELL` value. Existing Bash terminals stay running normally.

The repository's actual text font is Debian's **JetBrains Mono**, not a patched
Nerd Font. It is preserved along with Kitty's colour, opacity and padding values.
One `symbol_map` maps private-use glyphs to **Symbols Nerd Font Mono** from
Nerd Fonts **v3.4.0**, commit `fa7b859994228a9c8759f99c55a8d31ee92a1b5e`.
Only the symbol font and its upstream license are installed under
`$XDG_DATA_HOME/fonts/hyprixe-symbols`; other applications' fonts are not changed.
Fontconfig selection is checked before the shell changes. The pinned font covers
the Debian, branch and Python glyphs used by this prompt.

## Verify and customize

Log out, select **Hyprland (uwsm-managed)** in SDDM, log in and open Kitty:

```bash
zsh --version
echo "$SHELL"
ps -p $$ -o comm=
getent passwd "$(id -un)" | cut -d: -f7
zsh -lic 'print -r -- OK'
cd ~/hyprixe-debian
./verify.sh --dependencies --session
```

The shell fields should identify Zsh. `verify.sh` checks source syntax/order,
account shell, plugins, pinned assets/daemon, glyph font selection, Kitty's
default shell choice and silent login-interactive startup without a graphical
terminal. Existing Bash syntax/ShellCheck and session tests continue to run.
Native prompt/Git/Instant Prompt and account-restore validation is recorded in
[VALIDATION.md](VALIDATION.md). Physical Kitty rendering and the real SDDM login
still need a target-machine check.

The login-interactive probe should print `OK` without missing-file/plugin or
Instant Prompt warnings. It is a startup check, not a graphical terminal test.

The supplied configuration works immediately. **`p10k configure` is optional**:

```zsh
p10k configure
```

It can customize `.p10k.zsh`. A later full installation reapplies the managed
repository configuration with a new backup; keep long-term changes in your
repository/local branch. Save any later personal edits before restoring an
older deployment, since the normal restore mechanism protects changed files.
Restart Zsh/Kitty after editing startup configuration rather than repeatedly
sourcing `.zshrc` in the same shell.

## Restore

Use the normal dated transaction, without running the uninstaller as root:

```bash
./uninstall.sh --list
./uninstall.sh --backup=BACKUP_ID --dry-run
./uninstall.sh --backup=BACKUP_ID
```

The manifest records the previous shell and both dotfiles, including their old
contents/modes/symlinks. Restore verifies that the account and shell still match
the transaction before making changes, restores the old account shell through
`chsh`, and restores/removes managed files. A manually changed third shell or
edited managed file blocks restoration before any partial changes. Reconnect
after restoration to refresh `SHELL` again. Bash is never uninstalled; Debian
packages and personal shell history/cache files are retained. Upstream-generated
`.zwc` caches are not recursively erased along with possible personal files.

## Sources and credits

- [Powerlevel10k v1.20.0](https://github.com/romkatv/powerlevel10k/tree/v1.20.0), MIT,
  with its documented lean configuration API. The separately licensed
  [gitstatus v1.5.4](https://github.com/romkatv/gitstatus/tree/v1.5.4) daemon and
  integration retain their GNU GPLv3 notice in `gitstatus/LICENSE`.
- [Instant Prompt setup](https://github.com/romkatv/powerlevel10k#how-do-i-configure-instant-prompt).
- [Debian Zsh](https://packages.debian.org/trixie/zsh),
  [autosuggestions](https://packages.debian.org/trixie/zsh-autosuggestions) and
  [syntax-highlighting](https://packages.debian.org/trixie/zsh-syntax-highlighting).
- [Syntax-highlighting load order](https://github.com/zsh-users/zsh-syntax-highlighting/blob/master/INSTALL.md).
- [Nerd Fonts symbols v3.4.0](https://github.com/ryanoasis/nerd-fonts/tree/v3.4.0/patched-fonts/NerdFontsSymbolsOnly),
  with the font's upstream license retained alongside the installed font.
- [Kitty symbol mapping](https://sw.kovidgoyal.net/kitty/conf/#opt-kitty.symbol_map).
