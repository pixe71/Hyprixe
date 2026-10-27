"""Dolphin-only source, installed configuration and Qt 6 runtime checks."""
import argparse
import base64
import configparser
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dolphin_config import DATA_FILES, VISIBLE_GROUPS, read_ini, view_metadata

TOOLBAR = ['go_back', 'go_forward', 'go_up', 'url_navigators', 'edit_find', 'hamburger_menu']
PREFERENCES = {
    'General': {'GlobalViewProps': 'true', 'ShowStatusBar': 'Disabled', 'LockPanels': 'true', 'SplitView': 'false'},
    'IconsMode': {'IconSize': '96', 'PreviewSize': '96', 'MaximumTextLines': '2', 'TextWidthIndex': '2'},
    'InformationPanel': {'previewsShown': 'true', 'previewsAutoPlay': 'false', 'showHovered': 'false'},
    'MainWindow': {'MenuBar': 'Disabled'},
    'MainWindow][Toolbar mainToolBar': {'ToolButtonStyle': 'IconOnly'},
}
VIEW = {'Version': '4', 'ViewMode': '0', 'PreviewsShown': 'true', 'SortFoldersFirst': 'true'}


def assert_preferences(path):
    config = read_ini(path)
    for section, keys in PREFERENCES.items():
        for key, value in keys.items():
            if config.get(section, key, fallback=None) != value:
                raise ValueError(f'{path.name}: [{section}] {key} must be {value}')


def assert_toolbar(path):
    root = ET.parse(path).getroot()
    toolbar = root.find("ToolBar[@name='mainToolBar']")
    if toolbar is None or [a.get('name') for a in toolbar.findall('Action')] != TOOLBAR:
        raise ValueError('Dolphin toolbar must contain only navigation, location, search and menu')


def assert_view(config, native_defaults=False):
    for key, value in VIEW.items():
        # Dolphin omits default fields when saving to xattrs, and may remove
        # both storage forms when the entire global view uses native defaults.
        if config.get('Dolphin', key, fallback=value if native_defaults else None) != value:
            raise ValueError(f'Global view: {key} must be {value}')


def assert_information(config):
    if config.getint('Misc', 'version', fallback=0) < 13:
        raise ValueError('Baloo metadata initialization version must be at least 13')
    for key in ('kfileitem#type', 'kfileitem#size', 'kfileitem#modified'):
        # Baloo omits stored true values because true is its default.
        if not config.getboolean('Show', key, fallback=True):
            raise ValueError('Information panel property hidden: ' + key)
    for key in ('tags', 'rating', 'userComment'):
        if config.getboolean('Show', key, fallback=True):
            raise ValueError('Information-panel editor should be hidden: ' + key)


def layout_bytes(path):
    value = read_ini(path)['State']['State']
    state = base64.b64decode(value, validate=True)
    if not state.startswith(b'\x00\x00\x00\xff\x00\x00\x00\x00'):
        raise ValueError('Unsupported Qt dock-state header/version')
    for name in ('placesDock', 'infoDock'):
        if name.encode('utf-16-be') not in state:
            raise ValueError(f'Dock state missing {name}')
    return state


def check_source(report, root):
    root = Path(root)
    checks = (
        ('Dolphin preferences: 96 px icons, global icon view, locked panels, no menu/status bar',
         lambda: assert_preferences(root / '.config/dolphinrc')),
        ('Dolphin minimal navigation toolbar XML', lambda: assert_toolbar(root / '.local/share' / DATA_FILES[0])),
        ('Dolphin global view properties: icon mode, previews and folders first',
         lambda: assert_view(read_ini(root / '.local/share' / DATA_FILES[1]))),
        ('Dolphin standard Qt 6 dock preset', lambda: layout_bytes(root / 'dolphin/dock-layout.ini')),
        ('Dolphin information properties: type, size, modified; no tag/rating editors',
         lambda: assert_information(read_ini(root / '.config/baloofileinformationrc'))),
    )
    for label, function in checks:
        try:
            function()
        except (OSError, ValueError, KeyError, configparser.Error, ET.ParseError) as exc:
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
            # Preflight must also work from a TTY before any Wayland display.
            version = subprocess.run([binary, '--version'], env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                                     capture_output=True, text=True, timeout=10)
            match = re.search(r'dolphin\s+(\d+)\.(\d+)', version.stdout, re.I)
            if version.returncode or not match or tuple(map(int, match.groups())) < (25, 4):
                errors.append('Dolphin >= 25.04 (Debian 13) is required for the separate State dock layout')
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
    state = Path(environ.get('XDG_STATE_HOME', home / '.local/state'))
    try:
        assert_preferences(config / 'dolphinrc')
        assert_toolbar(data / DATA_FILES[0])
        layout_bytes(state / 'dolphinstaterc')
        directory = data / 'dolphin/view_properties/global'
        if (directory / '.directory').is_file():
            view = read_ini(directory / '.directory')
        else:
            metadata = view_metadata(directory)
            view = configparser.ConfigParser(interpolation=None, delimiters=('=',))
            view.optionxform = str
            if metadata['value'] is not None:
                view.read_string(base64.b64decode(metadata['value']).decode())
        assert_view(view, native_defaults=True)
        assert_information(read_ini(config / 'baloofileinformationrc'))
    except (OSError, ValueError, KeyError, configparser.Error, ET.ParseError) as exc:
        report(False, 'Installed Dolphin preferences, toolbar, state and view properties: ' + str(exc))
    else:
        report(True, 'Installed Dolphin preferences, toolbar, state and global view properties (.directory, native xattr or native defaults)')
    try:
        if (data / 'user-places.xbel').is_file():
            root = ET.parse(data / 'user-places.xbel').getroot()
            for group in VISIBLE_GROUPS:
                node = root.find(f"info/metadata[@owner='http://www.kde.org']/GroupState-{group}-IsHidden")
                if node is not None and node.text == 'true':
                    raise ValueError(group + ' group is hidden')
        # With no XBEL, KDE creates the default bookmarks and visible groups.
        report(True, 'Places/Devices groups are not hidden; device rows depend on real hardware')
    except (OSError, ValueError, ET.ParseError) as exc:
        report(False, 'Places/Devices visibility: ' + str(exc))
    try:
        theme = read_ini(config / 'Kvantum/kvantum.kvconfig')
        kde = read_ini(config / 'kdeglobals')
        qt = read_ini(config / 'qt6ct/qt6ct.conf')
        if theme['General']['theme'] != 'Frosted-Glass' or kde['KDE']['widgetStyle'].lower() != 'kvantum' or qt['Appearance']['style'].lower() != 'kvantum':
            raise ValueError('Kvantum Frosted-Glass must be selected in Kvantum/KDE/qt6ct')
        if kde['Icons']['Theme'] != 'breeze-dark':
            raise ValueError('Expected existing Breeze Dark icons')
        override = environ.get('QT_STYLE_OVERRIDE', '')
        if override and override.lower() != 'kvantum':
            raise ValueError('Conflicting QT_STYLE_OVERRIDE=' + override)
    except (OSError, ValueError, KeyError, configparser.Error) as exc:
        report(False, 'Installed Dolphin Qt/Kvantum/Breeze integration: ' + str(exc))
    else:
        report(True, 'Installed Frosted-Glass Kvantum, Qt/KDE style and Breeze icons; no conflicting style override')


def check_runtime(report):
    errors = runtime_errors()
    report(not errors, 'Dolphin Qt 6 linkage and Kvantum plugin' + (': ' + '; '.join(errors) if errors else ''))
    # Optional bindings give an actual style instantiation without a GUI window.
    probe = "from PyQt6.QtWidgets import QApplication; a=QApplication([]); print(a.style().objectName())"
    try:
        result = subprocess.run([sys.executable, '-c', probe], env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        report(False, 'Qt 6 style instantiation: ' + str(exc))
        return
    if 'No module named' in result.stderr:
        print('SKIPPED: Qt style instantiation (optional python3-pyqt6 unavailable)')
    else:
        report(result.returncode == 0 and result.stdout.strip().lower() == 'kvantum',
               'Actual Qt 6 style instantiation: ' + (result.stdout.strip() or result.stderr.strip()))
    if shutil.which('udisksctl'):
        try:
            devices = subprocess.run(['udisksctl', 'status'], capture_output=True, text=True, timeout=15)
            report(devices.returncode == 0, 'UDisks2 device enumeration' +
                   (': ' + devices.stderr.strip() if devices.returncode else ': available'))
        except (OSError, subprocess.TimeoutExpired) as exc:
            report(False, 'UDisks2 device enumeration: ' + str(exc))
    print('SKIPPED: active Dolphin widget positions, mounted-device rows and compositor blur require a visual session check')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dependencies', action='store_true', help='Check only Qt 6 Dolphin and Kvantum runtime before deployment')
    args = parser.parse_args()
    if args.dependencies:
        errors = runtime_errors()
        for error in errors:
            print('ERROR: ' + error, file=sys.stderr)
        if not errors:
            print('PASS: Dolphin Qt 6 and Kvantum runtime dependencies')
        return bool(errors)
    parser.error('Use verify.sh --dolphin to check deployed configuration')


if __name__ == '__main__':
    sys.exit(main())
