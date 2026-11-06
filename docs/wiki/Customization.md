# Customization

Keep lasting configuration changes in a local branch/fork, then deploy them.
A future installation can replace direct edits to managed `~/.config` files.
For an ordinary wallpaper change, use `hyprixe-theme apply IMAGE` instead of
editing configuration. See [Dynamic Theming](Dynamic-Theming).

## Where to edit

| Area | Canonical source |
| --- | --- |
| Dynamic palette/templates | `common/theme/` |
| Waybar | `common/config/hypr/waybar/` |
| Rofi common paint/layout | `common/config/hypr/rofi/themes/` |
| Wlogout | `common/config/wlogout/` |
| Kitty | `common/config/kitty/kitty.conf` |
| Zsh / prompt | `common/shell/.zshrc`, `.p10k.zsh` |
| Dolphin paint | `common/config/Kvantum/Frosted-Glass-Dolphin/` and its KDE colour scheme |
| Lock / idle | `common/config/hypr/hyprlock.conf`, `hypridle.conf` |
| Personal keybindings | `common/config/hypr/UserConfigs/user_keybinds.lua` |
| Input / monitors | Loaded modules under `common/config/hypr/UserConfigs/` |

Shared behaviour belongs in `common/`; platform installation belongs in
`profiles/`. Avoid usernames, fixed connector names and duplicated desktop
configuration. The Zsh source is a template with platform-rendered plugin paths;
do not source that template directly.

## Apply changes

```bash
git diff --check
./verify.sh
./install.sh native --dry-run
# Close Dolphin before full deployment.
./install.sh native
```

Only Waybar and Dolphin have public component-only installation modes.
After deployment, use the activation table in [Maintenance](Maintenance#activate-changes).
Then run `./verify.sh --dependencies --session` inside the desktop.

## Keep ownership clear

Rofi's common Rasi owns paint; launcher/window layouts share a separate file.
Generated dynamic colours belong in cache, not committed configuration files.
Kvantum's Dolphin variant is app-specific; do not replace colours globally in
its SVG or impose a new Dolphin layout to change paint.

For keybinding replacements, disable the existing `KOOLDOTS_BINDS["CHORD"]`
handle before registering another binding. Update the expected verifier contract
when intentionally changing defaults; do not hide duplicate enabled bindings.
Keep shell startup quiet for Powerlevel10k Instant Prompt and installation checks.
