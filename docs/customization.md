# Customization

[Documentation index](README.md)

## Work in the repository

The checkout is the source of truth. Keep long-term changes in a local branch
or fork, review `git diff`, deploy the relevant component and run verification.
Editing a deployed `~/.config` file alone is temporary: the next installation
can replace it, creating a backup but not merging every personal preference.

Use XDG-aware paths and existing helpers. Do not embed your username, display
name or a specific connector. Custom XDG roots must stay within your HOME.
Avoid changing generated deployment placeholders directly; the installer
renders them for the target account.

| Area | Source to edit | Apply / check |
| --- | --- | --- |
| Wallpaper | `wallpapers/min_forest.jpg` | Full deployment; restart wallpaper service; reopen menus/lock and refresh SDDM on next reboot |
| Waybar | `.config/hypr/waybar/configs/Frosted-Glass`, `style/Frosted-Glass.css` | Waybar-only install, restart service, `--waybar --session` |
| Rofi | `.config/hypr/rofi/themes/Frosted-Glass-Common.rasi` and layout-specific files | Full deployment; reopen menu |
| Wlogout | `.config/wlogout/layout`, `style.css`, icons | Full deployment; reopen menu; keep the action contract unless intentionally changing it |
| Kitty | `.config/kitty/kitty.conf` | Full deployment; new Kitty window |
| Zsh / prompt | `.zshrc`, `.p10k.zsh` | Full deployment; new shell; reconnect if the account shell changes |
| Dolphin paint | `.config/Kvantum/Frosted-Glass-Dolphin/`, `.local/share/color-schemes/HyprixeFrostedDolphin.colors` | Close Dolphin; Dolphin-only deployment; reopen |
| Hyprlock / idle | `.config/hypr/hyprlock.conf`, `hypridle.conf` | Full deployment; test lock manually / restart hypridle |
| Keybindings | `.config/hypr/UserConfigs/user_keybinds.lua` | Full deployment, compositor reload and live audit |
| Input / monitors | `.config/hypr/UserConfigs/` Lua settings and monitor modules | Inspect the actual load graph, deploy and reload |

See each component guide for complete paths and implementation details. The
full installer deploys all managed components, even when only one source file
was edited. The only public scoped deployment modes are Waybar and Dolphin.

## Keep shared theme ownership clear

Rofi's common Rasi owns colours, text, inputbar, selection, borders and scrollbars.
Application/window layout is shared separately; clipboard has a compact layout.
Do not copy the common paint into each menu. Waybar retains its own GTK CSS;
SDDM uses QML and cannot directly import those Rasi/GTK rules.

The wallpaper path is reused by the desktop, lock and Rofi preview. Replacing
the existing asset in the repository keeps those references coherent. A full
deployment also updates SDDM's system-readable copy. The fixed palette is not
automatically regenerated from the image.

Dolphin's app-specific light Kvantum variant leaves the global Qt theme and
personal panel layout alone. Its reproducible maintainer generator is
[tools/build-dolphin-theme.py](../tools/build-dolphin-theme.py). Keep generated
paint and the KDE colour scheme consistent; inspect the resulting diff.

## Shell and keyboard changes

`p10k configure` is optional and writes the active prompt file. Copy deliberate
results back into the repository before a later deployment, which reapplies
the managed default. Keep personal shell startup quiet so Instant Prompt and
the installer probe can detect actual failures.

For a keybinding replacement, first disable the matching `KOOLDOTS_BINDS`
handle in the personal override file, then register the replacement. Do not
leave two enabled callbacks for the same chord. The verifier's fixed binding
contract will need deliberate maintenance if you alter default shortcuts;
it is not a reason to hide a conflict. Default French keyboard settings can
be changed in the loaded input configuration without changing Bash scripts.

## Deploy and inspect

```bash
git diff --check
./verify.sh
./install.sh native --dry-run
# Close Dolphin before a full deployment.
./install.sh native
```

Apply the appropriate restart from [updating](update.md), then run
`./verify.sh --dependencies --session` inside the intended session. Always
review the visual result yourself; source checks do not judge design quality.
