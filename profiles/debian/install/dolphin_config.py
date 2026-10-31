"""Dolphin-only paint and color selection; layout keys are never changed."""

from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "scripts"))
from source_layout import ROOT as REPOSITORY_ROOT, source_path, configure_imports, shell_bytes
configure_imports()
import configparser
import base64
import errno
import os
from pathlib import Path
import shutil
import subprocess

THEME = 'Frosted-Glass-Dolphin'
THEME_FILES = tuple(f'Kvantum/{THEME}/{THEME}.{suffix}' for suffix in ('kvconfig', 'svg'))
SCHEME_FILE = 'color-schemes/HyprixeFrostedDolphin.colors'
SCHEME_NAME = 'Hyprixe Frosted Dolphin'
VIEW_XATTR = 'user.kde.fm.viewproperties#1'


def read_ini(path):
    # KConfig uses '=' only; ':' belongs to keys such as "screen: Width".
    parser = configparser.ConfigParser(interpolation=None, strict=True, delimiters=('=',))
    parser.optionxform = str
    text = Path(path).read_text()
    first = next((line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(('#', ';'))), '')
    # Older Dolphin KConfig files have entries before the first named group.
    parser.read_string(('[__root__]\n' if first and not first.startswith('[') else '') + text)
    return parser


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
        raise ValueError('Close all Dolphin windows/processes before updating its theme or restoring its interface; otherwise Dolphin may overwrite preferences on exit.')


def remove_key(text, section, key):
    current, output = '', []
    for line in text.splitlines(keepends=True):
        if line.strip().startswith('[') and line.strip().endswith(']'):
            current = line.strip()[1:-1]
        if current == section and line.split('=', 1)[0].strip() == key:
            continue
        output.append(line)
    return ''.join(output)


def payload(repo, roots, merge_ini, default_theme=None):
    repo = Path(repo)
    result = {roots['config'] / name: ((source_path(repo, '.config') / name).read_bytes(), 0o644) for name in THEME_FILES}
    target = roots['config'] / 'Kvantum/kvantum.kvconfig'
    old = target.read_text() if target.is_file() else ''
    settings = read_ini(target) if target.is_file() else configparser.ConfigParser(interpolation=None)
    updates = {}
    if settings.has_section('Applications'):
        for theme, applications in settings.items('Applications'):
            names = [name.strip() for name in applications.split(',') if name.strip()]
            if any(name.lower() == 'dolphin' for name in names):
                old = remove_key(old, 'Applications', theme)
                names = [name for name in names if name.lower() != 'dolphin']
                if names:
                    updates[theme] = ','.join(names)
    updates[THEME] = 'dolphin'
    if not target.exists() and default_theme:
        old = merge_ini(old, {'General': {'theme': default_theme}})
    result[target] = (merge_ini(old, {'Applications': updates}).encode(), 0o644)
    # KDE's per-application color manager can replace Kvantum's palette with
    # Breeze Light after startup. Select matching colors for Dolphin only.
    result[roots['data'] / SCHEME_FILE] = ((source_path(repo, '.local/share') / SCHEME_FILE).read_bytes(), 0o644)
    target = roots['config'] / 'dolphinrc'
    old = target.read_text() if target.is_file() else (source_path(repo, '.config/dolphinrc')).read_text() if default_theme else ''
    result[target] = (merge_ini(old, {'UiSettings': {'ColorScheme': SCHEME_NAME}}).encode(), 0o644)
    return result
