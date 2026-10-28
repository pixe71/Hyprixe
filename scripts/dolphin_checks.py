"""Dolphin paint checks. Never enforce a dock layout, icon size or view mode."""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dolphin_config import THEME, THEME_FILES, SCHEME_NAME, SCHEME_FILE, read_ini

ERRORS = (OSError, ValueError, KeyError, configparser.Error, ET.ParseError)


def assert_theme(config, svg):
    settings = read_ini(config)
    for key in ('composite', 'translucent_windows', 'blurring', 'popup_blurring'):
        if not settings.getboolean('%General', key):
            raise ValueError('Kvantum option must be enabled: ' + key)
    if not settings.getboolean('Hacks', 'transparent_dolphin_view'):
        raise ValueError('Kvantum transparent_dolphin_view must be enabled')
    if settings['GeneralColors']['window.color'] != '#e7e9e8' or settings['GeneralColors']['text.color'] != '#2d3437':
        raise ValueError('Dolphin must use the neutral off-white background and dark text palette')
    elements = {element.get('id'): element for element in ET.parse(svg).iter() if element.get('id')}
    for name, color, alpha in (('window-normal', '#e7e9e8', '.78'), ('dock-normal', '#d5d9d8', '.38')):
        style = dict(part.split(':', 1) for part in elements[name].get('style', '').split(';') if ':' in part)
        if style.get('fill') != color or style.get('fill-opacity') != alpha:
            raise ValueError(name + ': expected neutral light SVG paint with unchanged alpha')


def assert_color_scheme(path):
    settings = read_ini(path)
    if settings['General']['Name'] != SCHEME_NAME:
        raise ValueError('Matching Dolphin KDE color scheme missing')
    for section, key, color in (('Colors:Window', 'BackgroundNormal', '231,233,232'),
                                ('Colors:Window', 'ForegroundNormal', '45,52,55'),
                                ('Colors:Selection', 'BackgroundNormal', '196,220,226')):
        if settings[section][key] != color:
            raise ValueError('Dolphin KDE palette does not match Kvantum: ' + section + '/' + key)


def check_source(report, root):
    root = Path(root)
    def interface():
        spec = json.loads((root / 'dolphin/interface-baseline.json').read_text())
        for name, digest in spec['baseline_files'].items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
                raise ValueError('Pre-9259fa5 interface changed: ' + name)
        for name in ('.config/baloofileinformationrc', '.local/share/dolphin/view_properties/global/.directory', 'dolphin/dock-layout.ini'):
            if (root / name).exists():
                raise ValueError('Rejected interface preset reintroduced: ' + name)
    def theme():
        assert_theme(*(root / '.config' / name for name in THEME_FILES))
        assert_color_scheme(root / '.local/share' / SCHEME_FILE)
    def association():
        settings = read_ini(root / '.config/Kvantum/kvantum.kvconfig')
        if settings['Applications'][THEME] != 'dolphin' or settings['General']['theme'] != 'Frosted-Glass':
            raise ValueError('Only Dolphin should use the light variant; global Frosted-Glass stays selected')
    for label, function in (('Dolphin interface: exact pre-9259fa5 files; no forced view/dock preset', interface),
                            ('Dolphin Kvantum: neutral light SVG paint, transparent views and dark text', theme),
                            ('Kvantum application association: Dolphin-only paint', association)):
        try:
            function()
        except ERRORS as exc:
            report(False, label + ': ' + str(exc))
        else:
            report(True, label)


def runtime_errors():
    errors = []
    binary = shutil.which('dolphin')
    if not binary:
        errors.append('Dolphin is missing; install the Debian dolphin package')
    else:
        try:
            links = subprocess.run(['ldd', binary], capture_output=True, text=True, timeout=10)
            if links.returncode or 'libQt6Widgets.so' not in links.stdout or 'libQt5Widgets.so' in links.stdout:
                errors.append('Dolphin must link to Qt 6 Widgets (Debian 13 package)')
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append('Cannot inspect Dolphin Qt linkage: ' + str(exc))
    if not list(Path('/usr/lib').glob('**/qt6/plugins/styles/libkvantum.so')):
        errors.append('Qt 6 Kvantum style plugin missing; install qt6-style-kvantum')
    for name in ('kf6/kio/thumbnail.so', 'kf6/thumbcreator/imagethumbnail.so', 'kf6/thumbcreator/jpegthumbnail.so'):
        if not list(Path('/usr/lib').glob('**/qt6/plugins/' + name)):
            errors.append('Qt 6 preview plugin missing: ' + name + '; install kio-extras')
    if not shutil.which('udisksctl'):
        errors.append('Devices backend missing; install udisks2')
    return errors


def check_installed(report, environ=None):
    environ = os.environ if environ is None else environ
    home = Path(environ.get('HOME', Path.home()))
    config = Path(environ.get('XDG_CONFIG_HOME', home / '.config'))
    data = Path(environ.get('XDG_DATA_HOME', home / '.local/share'))
    try:
        assert_theme(*(config / name for name in THEME_FILES))
        if read_ini(config / 'dolphinrc').get('UiSettings', 'ColorScheme', fallback=None) != SCHEME_NAME:
            raise ValueError('Dolphin per-application color scheme is not selected')
        assert_color_scheme(data / SCHEME_FILE)
        settings = read_ini(config / 'Kvantum/kvantum.kvconfig')
        if settings['Applications'][THEME] != 'dolphin':
            raise ValueError('Dolphin-specific Kvantum association missing')
        for theme, apps in settings.items('Applications'):
            if theme != THEME and 'dolphin' in [name.strip().lower() for name in apps.split(',')]:
                raise ValueError('Conflicting Kvantum association: ' + theme)
        for name, section, key in (('kdeglobals', 'KDE', 'widgetStyle'), ('qt6ct/qt6ct.conf', 'Appearance', 'style')):
            path = config / name
            if path.is_file() and read_ini(path).get(section, key, fallback='kvantum').lower() != 'kvantum':
                raise ValueError('Conflicting Qt style in ' + name)
        override = environ.get('QT_STYLE_OVERRIDE', '')
        if override and override.lower() != 'kvantum':
            raise ValueError('Conflicting QT_STYLE_OVERRIDE=' + override)
    except ERRORS as exc:
        report(False, 'Installed Dolphin-only Kvantum paint: ' + str(exc))
    else:
        report(True, 'Installed Dolphin-only Kvantum paint; no conflicting Qt style (interface not prescribed)')


def check_runtime(report):
    errors = runtime_errors()
    report(not errors, 'Dolphin Qt 6 linkage, previews and Kvantum plugin' + (': ' + '; '.join(errors) if errors else ''))
    probe = '''from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication
import json
QCoreApplication.setApplicationName('dolphin')
a=QApplication(['dolphin'])
p=a.style().standardPalette()
print(json.dumps({'style':a.style().objectName(),'window':p.color(QPalette.ColorRole.Window).name(),'text':p.color(QPalette.ColorRole.Text).name()}))
'''
    try:
        result = subprocess.run([sys.executable, '-c', probe], env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                                capture_output=True, text=True, timeout=15)
        if 'No module named' in result.stderr:
            print('SKIPPED: Qt style/palette instantiation (optional python3-pyqt6 unavailable)')
        else:
            actual = json.loads(result.stdout) if result.returncode == 0 else {}
            ok = actual.get('style') == 'kvantum' and actual.get('window') == '#e7e9e8' and actual.get('text') == '#2d3437'
            report(ok, 'Actual Qt 6 Kvantum style and theme palette for Dolphin: ' + (str(actual) if actual else result.stderr.strip()))
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        report(False, 'Qt 6 style/palette instantiation: ' + str(exc))
    print('SKIPPED: visible transparency, compositor blur and unchanged on-screen interface require a real desktop check')


def blur_option_enabled(output):
    """Read current bool and legacy int getoption values, never the set flag."""
    try:
        values = json.loads(output)
    except ValueError:
        # Keep the JSON query, but also accept hyprctl's normal text output.
        values = {key.lower(): value.strip().lower() for key, value in re.findall(
            r'^\s*(bool|int)\s*:\s*([^\r\n]*)', output, re.MULTILINE | re.IGNORECASE)}
    if not isinstance(values, dict):
        return False
    if 'bool' in values:
        value = values['bool']
        return value is True or (isinstance(value, str) and value.strip().lower() == 'true')
    value = values.get('int')
    return (type(value) is int and value == 1) or (isinstance(value, str) and value.strip() == '1')


def check_session(report):
    """Inspect the UWSM manager and compositor; never dispatch changes."""
    try:
        result = subprocess.run(['systemctl', '--user', 'show-environment'], capture_output=True, text=True, timeout=10)
        env = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        report(result.returncode == 0 and env.get('QT_STYLE_OVERRIDE', '').lower() == 'kvantum',
               'UWSM/systemd user manager exports QT_STYLE_OVERRIDE=kvantum')
        blur = subprocess.run(['hyprctl', '-j', 'getoption', 'decoration:blur:enabled'], capture_output=True, text=True, timeout=10)
        report(blur.returncode == 0 and blur_option_enabled(blur.stdout),
               'Active Hyprland compositor blur enabled')
        pids = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'dolphin'], capture_output=True, text=True, timeout=10)
        for pid in pids.stdout.split():
            values = (Path('/proc') / pid / 'environ').read_bytes().split(b'\0')
            report(b'QT_STYLE_OVERRIDE=kvantum' in values, 'Running Dolphin exports QT_STYLE_OVERRIDE=kvantum (PID ' + pid + ')')
        if not pids.stdout.strip():
            print('SKIPPED: no running Dolphin process to inspect; open Dolphin and repeat --dolphin --session')
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        report(False, 'Live Dolphin/UWSM style chain: ' + str(exc))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dependencies', action='store_true', help='Check Qt 6 Dolphin and Kvantum runtime before deployment')
    args = parser.parse_args()
    if args.dependencies:
        errors = runtime_errors()
        for error in errors:
            print('ERROR: ' + error, file=sys.stderr)
        if not errors:
            print('PASS: Dolphin Qt 6 and Kvantum runtime dependencies')
        return bool(errors)
    parser.error('Use verify.sh --dolphin [--session] to check deployed configuration')


if __name__ == '__main__':
    sys.exit(main())
