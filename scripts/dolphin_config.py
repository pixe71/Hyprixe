"""Standard Dolphin/KDE configuration payload; no runtime window manipulation."""
import configparser
import base64
import errno
import os
from pathlib import Path
import shutil
import subprocess
from xml.dom import minidom
from xml.parsers.expat import ExpatError

CONFIG_FILES = ('dolphinrc', 'baloofileinformationrc')
DATA_FILES = ('kxmlgui5/dolphin/dolphinui.rc', 'dolphin/view_properties/global/.directory')
VISIBLE_GROUPS = ('Places', 'Devices', 'RemovableDevices')
VIEW_XATTR = 'user.kde.fm.viewproperties#1'


def read_ini(path):
    # KConfig uses '=' only; ':' belongs to keys such as "screen: Width".
    parser = configparser.ConfigParser(interpolation=None, strict=True, delimiters=('=',))
    parser.optionxform = str
    parser.read_string(Path(path).read_text())
    return parser


def show_places_groups(data):
    """Unhide the requested existing groups, retaining bookmarks and metadata.

Do not create an XBEL on fresh installs: KDE populates the standard locations
and unhides these groups itself. No home URL, device UUID or mount is invented.
"""
    try:
        document = minidom.parseString(data)
    except ExpatError as exc:
        raise ValueError(f'Cannot read user-places.xbel: {exc}') from exc
    root = document.documentElement
    if root.tagName != 'xbel':
        raise ValueError('Invalid user-places.xbel: expected xbel root')

    def child(parent, name, **attributes):
        for node in parent.childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.tagName == name and all(
                    node.getAttribute(key) == value for key, value in attributes.items()):
                return node
        node = document.createElement(name)
        for key, value in attributes.items():
            node.setAttribute(key, value)
        parent.appendChild(node)
        return node

    metadata = child(child(root, 'info'), 'metadata', owner='http://www.kde.org')
    changed = False
    for group in VISIBLE_GROUPS:
        node = child(metadata, f'GroupState-{group}-IsHidden')
        text = ''.join(part.data for part in node.childNodes if part.nodeType == part.TEXT_NODE)
        if text != 'false':
            for part in list(node.childNodes):
                node.removeChild(part)
            node.appendChild(document.createTextNode('false'))
            changed = True
    return document.toxml(encoding='UTF-8') if changed else data


def view_metadata(directory):
    """Dolphin 25.04 can migrate .directory to this ONE directory xattr."""
    try:
        value = os.getxattr(directory, VIEW_XATTR)
    except OSError as exc:
        if exc.errno in (errno.ENOENT, errno.ENODATA):
            return {'supported': True, 'value': None}
        if exc.errno in (errno.ENOTSUP, errno.EOPNOTSUPP):
            return {'supported': False, 'value': None}
        raise
    return {'supported': True, 'value': base64.b64encode(value).decode('ascii')}


def restore_view_metadata(directory, value):
    if value is None:
        try:
            os.removexattr(directory, VIEW_XATTR)
        except OSError as exc:
            if exc.errno not in (errno.ENOENT, errno.ENODATA, errno.ENOTSUP, errno.EOPNOTSUPP):
                raise
    else:
        Path(directory).mkdir(parents=True, exist_ok=True)
        os.setxattr(directory, VIEW_XATTR, base64.b64decode(value, validate=True))


def ensure_closed():
    if shutil.which('pgrep') and subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'dolphin'],
                                               stdout=subprocess.DEVNULL, check=False).returncode == 0:
        raise ValueError('Close all Dolphin windows/processes before installing or restoring its layout; otherwise Dolphin may overwrite it on exit.')


def payload(repo, roots, merge_ini):
    repo = Path(repo)
    result = {}
    for name in CONFIG_FILES:
        source = repo / '.config' / name
        data = source.read_bytes()
        target = roots['config'] / name
        if name == 'baloofileinformationrc':
            desired = read_ini(source)
            old = target.read_text() if target.is_file() else ''
            current = configparser.ConfigParser(interpolation=None, delimiters=('=',), strict=False)
            current.read_string(old)
            desired['Misc']['version'] = str(max(13, current.getint('Misc', 'version', fallback=0)))
            data = merge_ini(old, {section: dict(desired[section]) for section in desired.sections()}).encode()
        result[target] = (data, 0o644)
    for name in DATA_FILES:
        result[roots['data'] / name] = ((repo / '.local/share' / name).read_bytes(), 0o644)
    preset = read_ini(repo / 'dolphin/dock-layout.ini')
    target = roots['state'] / 'dolphinstaterc'
    old = target.read_text() if target.is_file() else ''
    result[target] = (merge_ini(old, {'State': {'State': preset['State']['State']}}).encode(), 0o644)
    places = roots['data'] / 'user-places.xbel'
    if places.is_file():
        result[places] = (show_places_groups(places.read_bytes()), 0o644)
    return result
