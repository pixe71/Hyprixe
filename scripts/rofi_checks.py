"""Check shared Rofi menus and assets without treating visuals as tests."""

from source_layout import ROOT as REPOSITORY_ROOT, source_path, configure_imports, shell_bytes
configure_imports()
import os
from pathlib import Path
import re

OVERLAY = 'themes/Frosted-Glass-Launcher.rasi'
COMMON = 'themes/Frosted-Glass-Common.rasi'


def imports(path, seen=None):
    """Follow the actual theme graph; existence alone cannot prove shared paint."""
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen:
        return seen
    text = path.read_text()
    seen.add(path)
    for name in re.findall(r'@(?:import|theme)\s+"([^"]+)"', text):
        imports(path.parent / name, seen)
    return seen


def source_errors(root):
    config = source_path(root, '.config/hypr')
    required = ('rofi/config-launcher.rasi', 'rofi/config-windows.rasi',
                'rofi/config-clipboard.rasi', 'rofi/config-calc.rasi', 'rofi/config.rasi',
                'rofi/0-shared-fonts.rasi', 'rofi/themes/Frosted-Glass.rasi',
                'rofi/' + OVERLAY, 'rofi/' + COMMON, 'scripts/RofiLauncher.sh', 'scripts/LaunchApp.sh',
                'scripts/LaunchTerminal.sh', 'scripts/WindowSwitcher.sh', 'scripts/ClipManager.sh', 'lua/keybinds.lua')
    errors = [f'Missing launcher file: {name}' for name in required if not (config / name).is_file()]
    if errors:
        return errors
    if not (source_path(root, 'wallpapers/min_forest.jpg')).is_file():
        errors.append('Missing original min_forest.jpg wallpaper')
    for name in required:
        if name.endswith('.sh') and not os.access(config / name, os.X_OK):
            errors.append(f'Launcher helper is not executable: {name}')
    wrapper = (config / 'rofi/config-launcher.rasi').read_text()
    for name in ('config.rasi', OVERLAY):
        if f'@import "{name}"' not in wrapper:
            errors.append(f'Launcher does not import {name}')
    shared = (config / 'rofi/themes/Frosted-Glass.rasi').read_text()
    if '@import "Frosted-Glass-Common.rasi"' not in shared:
        errors.append('All Rofi dialogs must import the common Frosted Glass paint')
    windows = (config / 'rofi/config-windows.rasi').read_text()
    if '@import "config-launcher.rasi"' not in windows:
        errors.append('Window switcher must reuse the application launcher shell')
    for name in ('config-clipboard.rasi', 'config-calc.rasi'):
        if '@import "config.rasi"' not in (config / 'rofi' / name).read_text():
            errors.append(name + ' must retain the common configuration')
    for path in (config / 'rofi').rglob('*.rasi'):
        if re.search(r'rgba?\(\s*0\s*,\s*0\s*,\s*0\s*[,)]|#000000\b', path.read_text(), re.I):
            errors.append('Obsolete black Rofi background: ' + path.name)
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
    for chord, script, theme in (('ALT + F10', 'WindowSwitcher.sh', 'config-windows.rasi'),
                                 ('SUPER + CTRL + V', 'ClipManager.sh', 'config-clipboard.rasi')):
        if '"' + chord + '", script("' + script + '")' not in (config / 'lua/keybinds.lua').read_text():
            errors.append(chord + ' no longer opens ' + script)
        if theme not in (config / 'scripts' / script).read_text():
            errors.append(script + ' does not use ' + theme)
    return errors


def check_source(report, root):
    errors = source_errors(root)
    report(not errors, 'Rofi menus: common glass paint/fonts, shared launcher/window shell and compact clipboard' +
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
        for name in (COMMON, 'config-windows.rasi', 'config-clipboard.rasi', 'config-calc.rasi'):
            if not (config / 'rofi' / name).is_file():
                errors.append(f'Missing installed shared Rofi file: {name}')
        for name in ('config.rasi', 'config-launcher.rasi', 'config-windows.rasi', 'config-clipboard.rasi', 'config-calc.rasi'):
            loaded = imports(config / 'rofi' / name)
            if (config / 'rofi' / COMMON).resolve() not in loaded:
                errors.append(name + ' does not load the installed common glass paint; reinstall')
            if name in ('config-launcher.rasi', 'config-windows.rasi') and (config / 'rofi' / OVERLAY).resolve() not in loaded:
                errors.append(name + ' does not load the shared wallpaper shell; reinstall')
        for path in (config / 'rofi').rglob('*.rasi'):
            for name in re.findall(r'@(?:import|theme)\s+"([^"]+)"', path.read_text()):
                if not (path.parent / name).is_file():
                    errors.append(f'Missing installed Rofi import: {path.name}: {name}')
        for name in ('RofiLauncher.sh', 'LaunchApp.sh', 'LaunchTerminal.sh', 'WindowSwitcher.sh', 'ClipManager.sh'):
            path = config / 'scripts' / name
            if not path.is_file() or not os.access(path, os.X_OK):
                errors.append(f'Missing/non-executable installed helper: {name}')
    except OSError as exc:
        errors.append(str(exc))
    report(not errors, 'Installed Rofi menus: shared imports, existing wallpaper and executable helpers' +
           (': ' + '; '.join(errors) if errors else ''))
