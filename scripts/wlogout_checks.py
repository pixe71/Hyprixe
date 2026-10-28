"""Validate Wlogout without opening a menu or executing session actions."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ACTIONS = ('lock', 'logout', 'shutdown', 'reboot')


def runtime_errors():
    errors = []
    if not shutil.which('wlogout'):
        errors.append('Wlogout missing; install the Debian wlogout package')
    if not list(Path('/usr/lib').glob('*/gdk-pixbuf-2.0/*/loaders/libpixbufloader[_-]svg.so')):
        errors.append('Wlogout SVG icon loader missing; install librsvg2-common')
    return errors


def layout_objects(text):
    # Wlogout 1.2.2 expects a stream of JSON objects, not a JSON array.
    decoder = json.JSONDecoder()
    objects = []
    text = text.lstrip()
    while text:
        value, end = decoder.raw_decode(text)
        objects.append(value)
        text = text[end:].lstrip()
    return objects


def validate(config):
    folder = Path(config) / 'wlogout'
    rows = layout_objects((folder / 'layout').read_text())
    expected = [dict(label=name, action='hyprixe-session ' + name, text=name.capitalize(), keybind=key)
                for name, key in zip(ACTIONS, ('l', 'e', 's', 'r'))]
    if rows != expected:
        raise ValueError('Expected only Lock | Logout | Shutdown | Reboot with their fixed actions')
    css = (folder / 'style.css').read_text()
    if any('bind "' + key + '"' not in css for key in ('Left', 'Right', 'Up', 'Down', 'Return', 'KP_Enter')):
        raise ValueError('Wlogout GTK keyboard navigation bindings are missing')
    icons = re.findall(r'url\("([^"]+)"\)', css)
    if set(icons) != {'icons/' + name + '.svg' for name in ACTIONS}:
        raise ValueError('The four local Wlogout icons must resolve')
    for name in icons:
        ET.parse(folder / name)
    if re.search(r'/home/|Virtual-1|killall|pkill|hibernate|suspend', css + str(rows), re.I):
        raise ValueError('Machine-specific path or unsupported session action')


def check_css(report, path):
    # PyGObject is available with Blueman on Debian; keep it optional for source
    # verification on minimal hosts. The native GTK parser needs no window.
    code = '''import gi,sys
gi.require_version('Gtk','3.0')
from gi.repository import Gtk
Gtk.CssProvider().load_from_path(sys.argv[1])
'''
    result = subprocess.run([sys.executable, '-c', code, str(path)], capture_output=True, text=True)
    if 'No module named' in result.stderr or 'Namespace Gtk not available' in result.stderr:
        print('SKIPPED: native Wlogout CSS parser (optional PyGObject/GTK introspection unavailable)')
        return
    report(result.returncode == 0, 'Wlogout CSS: native GTK 3 parser' +
           (': ' + result.stderr.strip() if result.returncode else ' accepted'))


def check_source(report, root):
    root = Path(root)
    try:
        validate(root / '.config')
        binding = (root / '.config/hypr/lua/keybinds.lua').read_text()
        if binding.count('bind("SUPER + Backspace", d.exec_cmd("hyprixe-session")') != 1:
            raise ValueError('SUPER + Backspace must launch hyprixe-session exactly once')
        if '"logout_dialog"' not in (root / '.config/hypr/lua/rules.lua').read_text():
            raise ValueError('The Wlogout layer-shell namespace needs the existing Frosted blur rule')
        if not (root / '.local/bin/hyprixe-session').is_file():
            raise ValueError('Wlogout launcher/action helper is missing')
    except (OSError, ValueError, ET.ParseError) as exc:
        report(False, 'Wlogout source: ' + str(exc))
        return
    report(True, 'Wlogout source: four ordered actions, local SVGs, SUPER + Backspace and logout_dialog blur')
    check_css(report, root / '.config/wlogout/style.css')
    print('SKIPPED: Wlogout physical input, hover, toggle and Hyprland blur need interactive testing')


def check_installed(report, root):
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    try:
        validate(config)
        launcher = Path.home() / '.local/bin/hyprixe-session'
        if not launcher.is_file() or not os.access(launcher, os.X_OK):
            raise ValueError('Installed hyprixe-session must exist and be executable')
        if launcher.read_bytes() != (Path(root) / '.local/bin/hyprixe-session').read_bytes():
            raise ValueError('Installed hyprixe-session differs from this checkout; reinstall')
        for name in ('hypr/scripts/LockScreen.sh', 'hypr/rofi/config.rasi'):
            if not (config / name).is_file():
                raise ValueError('Required Wlogout action file missing: ' + name)
        if not os.access(config / 'hypr/scripts/LockScreen.sh', os.X_OK):
            raise ValueError('LockScreen.sh must be executable')
        missing = [name for name in ('wlogout', 'hyprixe-session', 'hyprctl', 'uwsm', 'rofi', 'systemctl', 'hyprlock', 'python3')
                   if not shutil.which(name)]
        if missing:
            raise ValueError('Wlogout/action commands missing: ' + ', '.join(missing))
        errors = runtime_errors()
        if errors:
            raise ValueError('; '.join(errors))
    except (OSError, ValueError, ET.ParseError) as exc:
        report(False, 'Installed Wlogout integration: ' + str(exc))
    else:
        report(True, 'Installed Wlogout: four actions, assets, executable helper and action dependencies')
