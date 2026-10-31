"""One-off, backup-based rollback of interface commit 9259fa5, not the desktop."""

from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "scripts"))
from source_layout import ROOT as REPOSITORY_ROOT, source_path, configure_imports, shell_bytes
configure_imports()
import base64
import json
from pathlib import Path
from xml.dom import minidom

FILES = (('config', 'dolphinrc'), ('config', 'baloofileinformationrc'),
         ('data', 'kxmlgui5/dolphin/dolphinui.rc'),
         ('data', 'dolphin/view_properties/global/.directory'), ('state', 'dolphinstaterc'))
MARKER = 'hyprixe/dolphin-interface-restored-9259fa5.json'


def bookmark_flags(current, previous):
    """Revert only the flags changed by us, retaining newly added bookmarks."""
    now, old = minidom.parseString(current), minidom.parseString(previous)
    def meta(doc):
        root = doc.documentElement
        info = next((x for x in root.childNodes if getattr(x, 'tagName', '') == 'info'), None)
        if info is None:
            info = doc.createElement('info'); root.insertBefore(info, root.firstChild)
        node = next((x for x in info.childNodes if getattr(x, 'tagName', '') == 'metadata' and
                     x.getAttribute('owner') == 'http://www.kde.org'), None)
        if node is None:
            node = doc.createElement('metadata'); node.setAttribute('owner', 'http://www.kde.org'); info.appendChild(node)
        return node
    target, source = meta(now), meta(old)
    for group in ('Places', 'Devices', 'RemovableDevices'):
        tag = 'GroupState-' + group + '-IsHidden'
        for node in list(target.childNodes):
            if getattr(node, 'tagName', '') == tag:
                target.removeChild(node)
        for node in source.childNodes:
            if getattr(node, 'tagName', '') == tag:
                target.appendChild(now.importNode(node, True))
    return now.toxml(encoding='UTF-8')


def plan(repo, roots, home, read_manifest, digest, guard, backup_id=None):
    marker = roots['state'] / MARKER
    if marker.exists():
        print('The pre-9259fa5 Dolphin interface has already been restored; keeping the current interface.')
        return {}, None
    spec = json.loads((source_path(repo, 'dolphin/interface-baseline.json')).read_text())
    backups = roots['state'] / 'hyprixe/backups'
    if backup_id and (Path(backup_id).name != backup_id or backup_id in ('.', '..')):
        raise ValueError('Use a backup ID from uninstall.sh --list')
    candidates = [backups / backup_id] if backup_id else sorted(backups.glob('*'))
    toolbar = str(roots['data'] / 'kxmlgui5/dolphin/dolphinui.rc')
    selected = None
    for backup in candidates:
        guard(backup / 'manifest.json', home)
        if not (backup / 'complete').is_file() or not (backup / 'manifest.json').is_file():
            continue
        manifest = read_manifest(backup)
        if manifest.get('home') != str(home) or manifest.get('restored'):
            continue
        if any(e['target'] == toolbar and e['after'] in spec['bad_toolbar_sha256'] and
               e['before'] not in spec['bad_toolbar_sha256'] for e in manifest['files']):
            selected = backup, manifest
            break
    if selected is None:
        raise ValueError('No intact pre-9259fa5 Dolphin interface backup found. No interface was guessed or changed. '
                         'Use uninstall.sh --list and --interface-backup ID, or recover your original Dolphin state first.')
    backup, manifest = selected
    entries = {e['target']: e for e in manifest['files']}
    def original(entry):
        if entry['backup'] is None:
            return None
        name = entry['backup']
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError('Invalid interface backup filename')
        source = backup / 'files' / name
        if source.is_symlink():
            raise ValueError('Original interface uses a symlink; restore that saved link explicitly instead of guessing its contents')
        if digest(source) != entry['before']:
            raise ValueError('Original Dolphin interface backup is corrupt: ' + str(source))
        return source.read_bytes()
    files = {}
    for root, name in FILES:
        target = roots[root] / name
        guard(target, home)
        if str(target) in entries:
            entry = entries[str(target)]
            files[target] = (original(entry), entry['mode'])
    places = roots['data'] / 'user-places.xbel'
    if str(places) in entries and places.is_file():
        before = original(entries[str(places)])
        if before is not None:
            files[places] = (bookmark_flags(places.read_bytes(), before), 0o644)
    attribute = None
    view = manifest.get('dolphin_view_xattr')
    if view:
        if view['path'] != str(roots['data'] / 'dolphin/view_properties/global'):
            raise ValueError('The original view metadata belongs to different XDG paths')
        if view['before'] is not None:
            base64.b64decode(view['before'], validate=True)
        attribute = {'value': view['before']}
    files[marker] = ((json.dumps({'layout_commit_reverted': '9259fa5', 'source_backup': backup.name}, indent=2) + '\n').encode(), 0o600)
    print('Restoring only Dolphin interface files from:', backup.name)
    print('Bookmarks added since that backup are retained; other desktop files are not restored.')
    return files, attribute
