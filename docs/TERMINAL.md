# Kitty Frosted Glass

Kitty is the active terminal for `SUPER + Return`, `TERMINAL`, the KoolDots
defaults, Rofi terminal applications and KDE's external-terminal action.
The binding keeps the existing `LaunchTerminal.sh` wrapper, which launches
`uwsm app -- kitty "$@"`. No additional session service or terminal autostart
is introduced. See the [UWSM application guidance](https://github.com/Vladimir-csp/uwsm#applications-and-autostart).

## Appearance and defaults

`.config/kitty/kitty.conf` uses the existing terminal palette: dark `#122434`
background, light `#e6f1f4` text, cyan selection `#7ed6ff` and `#b4f9f8` links.
Background opacity is **0.92**, font size 12 pt and padding 10 px. Hyprland's
existing window opacity, blur and rounding remain unchanged; they also affect
Kitty. No terminal-specific compositor rule or graphics override is added.

Debian's `fonts-jetbrains-mono` supplies **JetBrains Mono**. A patched
JetBrainsMono Nerd Font is not bundled by Hyprixe. If you already installed
that variant, you can select its exact family in your local Kitty config;
`fc-match 'JetBrainsMono Nerd Font'` shows which font actually resolves.
The default setup uses the packaged family rather than relying on a missing
Nerd Font and silently getting a substitute.

Kitty's default selection, links, tabs, splits and keyboard mappings remain
available. Copy/paste uses `CTRL + SHIFT + C` / `CTRL + SHIFT + V`; scrollback
keeps 10,000 lines. No custom Kitty keybindings are installed. See the
[Debian 13 Kitty configuration manual](https://manpages.debian.org/trixie/kitty/kitty.conf.5.en.html).

## Migration and restore

```bash
cd ~/hyprixe-debian
git pull
# Close Dolphin first, as required by the existing full installer.
./install.sh native
./verify.sh
```

The full installer installs the Debian stable `kitty` package, checks the
binary, font and real Kitty config parser, and deploys the config through the
existing dated backup transaction. Existing `kitty/kitty.conf` is backed up
before replacement, including with customized XDG paths. KDE's unrelated
settings are retained. No terminal is launched during installation.

Alacritty is no longer required or shipped. The installer **does not uninstall
its package or remove personal Alacritty files**. Existing copies under your
HOME can remain without participating in Hyprixe. Historical audits and
generic optional upstream examples can still mention Alacritty.

Save your work and log out; choose **Hyprland (uwsm-managed)** in SDDM again.
A fresh login ensures `TERMINAL=kitty` reaches both Hyprland and the systemd
activation environment. Test `SUPER + Return`, then run inside that session:

```bash
kitty --version
fc-match 'JetBrains Mono'
./verify.sh --dependencies --session
```

The session audit queries `hyprctl -j binds` and retained Lua handles. It also
checks the loaded Kitty default, `TERMINAL`, Kitty's bind description and the
installed launcher. Lua bind JSON contains a callback ID rather than its
command body; the verifier therefore does not claim JSON alone proves a
Kitty process was launched. Pressing the shortcut remains an interactive test.

To undo the migration, restore its dated transaction using the normal
`./uninstall.sh --list` and `./uninstall.sh --backup=ID` workflow, then log in
again. Restore does not remove Debian packages. If other installations followed
this one, inspect their transactions first; restore refuses conflicting edits.
