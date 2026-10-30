# Screenshot privacy review and final capture checklist

[Documentation index](../README.md) · [Asset rights](../assets-provenance.md)

Review date: **2026-10-30**. All three current 1366×768 PNGs were viewed.
Their PNG chunks contain only IHDR/IDAT/IEND: no text, EXIF or XMP metadata
was found. No image was edited, deleted, cropped, blurred or re-encoded.

## Current captures

| File | Decision | Evidence / remaining condition |
| --- | --- | --- |
| [screenshot1.png](screenshot1.png) | **Replace or omit before publication** | Fastfetch exposes a personal account identifier, hostname and LAN IPv4 address, plus a hardware profile. It is no longer embedded in the main README. The file remains unchanged locally and must not be included in a public release as-is. |
| [screenshot2.png](screenshot2.png) | **May retain for privacy** | Wlogout only; no readable account, email, token, IP, sensitive path or hostname observed. Publication still depends on clearing the wallpaper rights. |
| [screenshot3.png](screenshot3.png) | **May retain for privacy** | Rofi applications and Waybar; no readable personal identifier observed. Publication still depends on clearing the wallpaper rights. |

The terminal capture reports Hyprland 0.55.2. It must not be captioned as a
0.56.2 validation result. A privacy review is not a copyright clearance or
proof that every graphical interaction was tested. The removed historical
`screenshot.png` is not linked or restored.

## Final six captures

Suggested filenames below are plans, not links to nonexistent files.
Only add README embeds after actual approved files exist.

- [ ] **Desktop** (`desktop.png`): clean forest desktop with four workspaces
  and the complete bar; no terminal/system-info overlay or private notification.
- [ ] **Waybar** (`waybar.png`): readable tray/workspaces/taskbar, center metrics
  and right-side modules. Close personal tray popups, SSID/IP tooltips and
  notifications; hide private window titles. If no battery exists, caption that
  fact rather than fabricating a widget.
- [ ] **SUPER + Space** (`launcher.png`): wallpaper/sidebar plus applications
  and search, no personal search history, file path or account details.
  Existing capture 3 can fill this slot after asset rights are cleared.
- [ ] **Wlogout** (`wlogout.png`): one horizontal Lock/Logout/Shutdown/Reboot
  menu, no private background content. Existing capture 2 can fill this slot
  after asset rights are cleared.
- [ ] **Kitty + Zsh + Powerlevel10k/Git** (`kitty-zsh-git.png`): a disposable
  demo repository with neutral path/branch/file names, a readable prompt and
  clean/dirty state. No fastfetch identity/network output, Git remote URL,
  email, real HOME path, account-context segment or shell-history disclosure.
  Use a deliberate demo account/environment for this capture if needed; do
  not change the project's default prompt just to hide a personal capture.
- [ ] **Dolphin/Kvantum** (`dolphin.png`): accepted panel/toolbar layout and
  light translucent glass, using a neutral demo folder. Check location bar,
  Places/bookmarks, device labels, previews and metadata for personal content.

## Before accepting any image

- [ ] Artwork/theme rights are cleared for the release and its screenshots.
- [ ] No full name, email, token, account identifier or personal hostname.
- [ ] No unnecessary public/private IP, SSID, remote account/URL or sensitive path.
- [ ] No secrets in clipboard, terminal history, notifications, taskbar titles
  or background windows; inspect all corners and tooltips at full size.
- [ ] No personal metadata in PNG/JPEG ancillary fields; review the actual file.
- [ ] Caption the actual system/version and distinguish screenshots from test evidence.
- [ ] Intentionally replace/omit capture 1 before staging the public release.

The six slots remain unchecked until the final publication set is reviewed.
SDDM, Hyprlock, clipboard and window-switcher captures are useful optional
additions, subject to the same privacy and asset checks. Do not create fake
screenshots or automatic redactions as part of this release-preparation task.
