"""Check the application launcher's assets without treating visuals as tests."""
import os
from pathlib import Path
import re

OVERLAY = 'themes/Frosted-Glass-Launcher.rasi'


def source_errors(root):
    config = root / '.config/hypr'
    required = ('rofi/config-launcher.rasi', 'rofi/config.rasi',
                'rofi/0-shared-fonts.rasi', 'rofi/themes/Frosted-Glass.rasi',
                'rofi/' + OVERLAY, 'scripts/RofiLauncher.sh', 'scripts/LaunchApp.sh',
                'scripts/LaunchTerminal.sh', 'scripts/WindowSwitcher.sh', 'lua/keybinds.lua')
    errors = [f'Missing launcher file: {name}' for name in required if not (config / name).is_file()]
    if errors:
        return errors
    if not (root / 'wallpapers/min_forest.jpg').is_file():
        errors.append('Missing original min_forest.jpg wallpaper')
    for name in required:
        if name.endswith('.sh') and not os.access(config / name, os.X_OK):
            errors.append(f'Launcher helper is not executable: {name}')
    wrapper = (config / 'rofi/config-launcher.rasi').read_text()
    for name in ('config.rasi', OVERLAY):
        if f'@import "{name}"' not in wrapper:
            errors.append(f'Launcher does not import {name}')
    theme = (config / 'rofi' / OVERLAY).read_text()
    actions = dict(re.findall(r'(button-\w+)\s*\{[^{}]*action:\s*"([^"]+)"', theme))
    expected = {'button-applications': 'kb-custom-1', 'button-files': 'kb-custom-17',
                'button-windows': 'kb-custom-18', 'button-terminal': 'kb-custom-19'}
    if actions != expected:
        errors.append('Launcher must expose exactly Applications / Files / Windows / Terminal')
    image = '$HOME/.local/share/hyprixe/wallpapers/min_forest.jpg'
    if image not in theme or 'background-image:' not in theme:
        errors.append('Launcher must reference the existing installed Hyprixe wallpaper')
    launcher = (config / 'scripts/RofiLauncher.sh').read_text()
    if 'config-launcher.rasi' not in launcher or '-hyprixe-launcher' not in launcher:
        errors.append('SUPER + Space helper does not use the dedicated launcher configuration')
    if '"SUPER + Space", script("RofiLauncher.sh")' not in (config / 'lua/keybinds.lua').read_text():
        errors.append('SUPER + Space no longer opens RofiLauncher.sh')
    return errors


def check_source(report, root):
    errors = source_errors(root)
    report(not errors, 'Rofi launcher: shared theme/fonts, wallpaper, four actions and SUPER + Space' +
           (': ' + '; '.join(errors) if errors else ''))


def check_installed(report):
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'hypr'
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    errors = []
    try:
        wrapper = (config / 'rofi/config-launcher.rasi').read_text()
        theme = (config / 'rofi' / OVERLAY).read_text()
        wallpaper = data / 'hyprixe/wallpapers/min_forest.jpg'
        if str(wallpaper) not in theme:
            errors.append('Launcher wallpaper path does not match XDG_DATA_HOME; reinstall')
        if not wallpaper.is_file():
            errors.append(f'Missing wallpaper: {wallpaper}')
        for name in ('config.rasi', OVERLAY):
            if f'@import "{name}"' not in wrapper or not (config / 'rofi' / name).is_file():
                errors.append(f'Missing installed launcher import: {name}')
        for name in ('RofiLauncher.sh', 'LaunchApp.sh', 'LaunchTerminal.sh', 'WindowSwitcher.sh'):
            path = config / 'scripts' / name
            if not path.is_file() or not os.access(path, os.X_OK):
                errors.append(f'Missing/non-executable installed helper: {name}')
    except OSError as exc:
        errors.append(str(exc))
    report(not errors, 'Installed Rofi launcher: configuration, existing wallpaper and executable helpers' +
           (': ' + '; '.join(errors) if errors else ''))
