"""Install/restore the Hyprixe SDDM theme/input method, with root-owned backups.

No display-manager restart, PAM change, autologin change or session-file write.
"""

from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "scripts"))
from source_layout import ROOT as REPOSITORY_ROOT, source_path, configure_imports, shell_bytes
configure_imports()
import argparse
import configparser
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import stat
import sys
import uuid
from deploy import atomic, digest, merge_ini

REPO = REPOSITORY_ROOT
THEME = 'hyprixe-frosted'
THEME_DIR = '/usr/share/sddm/themes/' + THEME
CONFIG = '/etc/sddm.conf.d/zz-hyprixe-theme.conf'
BACKUPS = '/var/lib/hyprixe/sddm/backups'
SESSION = '/usr/share/wayland-sessions/hyprland-uwsm.desktop'
FILES = ('Main.qml', 'metadata.desktop', 'theme.conf', 'components/GlassPane.qml',
         'components/GlassButton.qml', 'components/GlassComboBox.qml', 'assets/user.svg')
QML_PACKAGES = ('qml6-module-qtquick', 'qml6-module-qtquick-window',
                'qml6-module-qtquick-controls', 'qml6-module-qtquick-templates',
                'qml6-module-qtquick-layouts', 'qml6-module-qtquick-effects',
                'qml6-module-qtqml-workerscript', 'libqt6svg6')
MANAGED_SETTINGS = {'Theme': {'Current': THEME, 'ThemeDir': '/usr/share/sddm/themes'},
                    'General': {'InputMethod': ''}}


def virtual_keyboard_sources(theme):
    """Reject a theme-side panel or explicit request to show a virtual keyboard."""
    pattern = re.compile(r'QtQuick\.VirtualKeyboard|\b(?:InputPanel|VirtualKeyboard|InputPanelLoader)\b|Qt\.inputMethod\.show\s*\(')
    hits = []
    for path in theme.rglob('*.qml'):
        source = re.sub(r'/\*.*?\*/|//[^\n]*', '', path.read_text(), flags=re.S)
        if pattern.search(source):
            hits.append(str(path.relative_to(theme)))
    return hits


def source_payload(repo=REPO):
    source = source_path(repo, 'sddm/themes') / THEME
    forced = virtual_keyboard_sources(source)
    if forced:
        raise ValueError('Theme must not force a virtual keyboard: ' + ', '.join(forced))
    result = {}
    for name in FILES:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing or symlinked SDDM theme source: {path}')
        result[THEME_DIR + '/' + name] = path.read_bytes()
    result[THEME_DIR + '/min_forest.jpg'] = (source_path(repo, 'wallpapers/min_forest.jpg')).read_bytes()
    return result


def session_error(path):
    try:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read_string(path.read_text())
        entry = parser['Desktop Entry']
        if (entry.get('Name') != 'Hyprland (uwsm-managed)' or
                shlex.split(entry.get('Exec', '')) != ['uwsm', 'start', '-e', '-D', 'Hyprland', 'hyprland.desktop'] or
                entry.get('Hidden', 'false').lower() == 'true'):
            return 'Hyprland (uwsm-managed) desktop entry is hidden or has unexpected Name/Exec values'
    except (OSError, KeyError, ValueError, configparser.Error) as exc:
        return f'Hyprland (uwsm-managed) session entry is missing/invalid: {exc}'
    return None


def prerequisites():
    if not shutil.which('sddm') or not shutil.which('sddm-greeter-qt6'):
        raise ValueError('SDDM with its Qt 6 greeter must already be installed. This installer does not replace your display manager.')
    problem = session_error(Path(SESSION))
    if problem:
        raise ValueError(problem)
    import subprocess
    missing = []
    for package in QML_PACKAGES:
        result = subprocess.run(['dpkg-query', '-W', '-f=${db:Status-Status}', package], capture_output=True, text=True)
        if result.returncode or result.stdout.strip() != 'installed':
            missing.append(package)
    if missing:
        raise ValueError('Missing SDDM Qt 6 dependencies: ' + ', '.join(missing))


def neutralize_managed_keys(text):
    # Move only theme selection and the desktop input-method choice to our
    # snippet. Preserve DisplayServer, Autologin and session configuration.
    section = ''
    output = []
    for line in text.splitlines(keepends=True):
        header = re.match(r'^\s*\[([^]]+)\]', line)
        if header:
            section = header.group(1)
        key = line.split('=', 1)[0].strip() if '=' in line else None
        if key in MANAGED_SETTINGS.get(section, {}):
            output.append('# Hyprixe: ' + section + '.' + key + ' is managed by zz-hyprixe-theme.conf\n')
        else:
            output.append(line)
    return ''.join(output)


class SystemTheme:
    def __init__(self, root=Path('/'), repo=REPO, actor_uid=None):
        self.root = Path(root).resolve()
        self.repo = repo
        self.actor_uid = os.getuid() if actor_uid is None else actor_uid

    def path(self, absolute):
        return self.root / absolute.lstrip('/')

    def guard(self, path, directory=False):
        relative = path.relative_to(self.root).as_posix()
        allowed = (relative == 'etc/sddm.conf' or
                   (path.parent == self.path('/etc/sddm.conf.d') and path.suffix == '.conf') or
                   relative.startswith(THEME_DIR.lstrip('/') + '/'))
        if directory:
            allowed = relative in ('etc/sddm.conf.d', THEME_DIR.lstrip('/')) or relative.startswith(THEME_DIR.lstrip('/') + '/')
        if not allowed or '..' in path.parts:
            raise ValueError(f'Refusing SDDM target outside the allowed paths: {path}')
        for parent in path.parents:
            if parent == self.root:
                break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise ValueError(f'Symlinked/non-directory SDDM parent: {parent}')
        if path.is_symlink() or (not directory and path.exists() and not path.is_file()):
            raise ValueError(f'SDDM target must be a regular file: {path}')

    def guard_state(self, path):
        if not path.is_relative_to(self.path('/var/lib/hyprixe/sddm')):
            raise ValueError('Invalid SDDM state path')
        for parent in (path, *path.parents):
            if parent == self.root:
                break
            if parent.is_symlink():
                raise ValueError(f'Symlinked SDDM backup/state path: {parent}')

    def config_files(self):
        return [*sorted(self.path('/usr/lib/sddm/sddm.conf.d').glob('*.conf')),
                *sorted(self.path('/etc/sddm.conf.d').glob('*.conf')),
                self.path('/etc/sddm.conf')]

    def configuration(self):
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        for path in self.config_files():
            if path.exists():
                parser.read_string(path.read_text(), source=str(path))
        return parser

    def effective_theme(self):
        parser = self.configuration()
        return (parser.get('Theme', 'Current', fallback=''),
                parser.get('Theme', 'ThemeDir', fallback='/usr/share/sddm/themes'))

    def payload(self):
        directories = self.configuration().get('Wayland', 'SessionDir', fallback='/usr/local/share/wayland-sessions,/usr/share/wayland-sessions')
        if '/usr/share/wayland-sessions' not in [item.strip().rstrip('/') for item in directories.split(',')]:
            raise ValueError('SDDM [Wayland] SessionDir excludes the Debian UWSM session directory. Keep /usr/share/wayland-sessions available.')
        content = {self.path(name): data for name, data in source_payload(self.repo).items()}
        config = self.path(CONFIG)
        self.guard(config)
        content[config] = merge_ini(config.read_text() if config.exists() else '', MANAGED_SETTINGS).encode()
        # /etc/sddm.conf is read last by SDDM, regardless of snippet names.
        higher = [p for p in self.path('/etc/sddm.conf.d').glob('*.conf') if p.name > config.name]
        higher.append(self.path('/etc/sddm.conf'))
        for path in higher:
            self.guard(path)
            if path.exists():
                before = path.read_text()
                after = neutralize_managed_keys(before)
                if before != after:
                    content[path] = after.encode()
        for path in content:
            self.guard(path)
            if path.is_relative_to(self.path(THEME_DIR)):
                for parent in path.parents:
                    if parent == self.root:
                        break
                    if parent.exists() and parent.stat().st_mode & 0o001 == 0:
                        raise ValueError(f'SDDM theme directory must be traversable by the greeter: {parent}')
        return content

    def install(self, dry=False):
        content = self.payload()
        changes = [(path, data) for path, data in content.items()
                   if digest(path) != hashlib.sha256(data).hexdigest() or
                   (path.is_relative_to(self.path(THEME_DIR)) and stat.S_IMODE(path.stat().st_mode) != 0o644)]
        if dry:
            for path, _ in changes:
                print('SDDM INSTALL (backed up)', path)
            return None
        if not changes:
            return None
        identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-sddm-' + uuid.uuid4().hex[:8]
        backup = self.path(BACKUPS) / identifier
        self.guard_state(backup)
        backup.mkdir(parents=True, mode=0o700)
        (backup / 'files').mkdir(mode=0o700)
        manifest = {'format': 1, 'kind': 'sddm', 'id': identifier, 'root': str(self.root),
                    'actor_uid': self.actor_uid, 'files': [], 'directories': []}
        for i, (path, data) in enumerate(changes):
            old = path.stat() if path.exists() else None
            if old:
                shutil.copy2(path, backup / 'files' / str(i))
            manifest['files'].append({'target': str(path), 'before': digest(path),
                                      'after': hashlib.sha256(data).hexdigest(),
                                      'backup': str(i) if old else None,
                                      'mode': stat.S_IMODE(old.st_mode) if old else 0o644,
                                      'uid': old.st_uid if old else os.getuid(),
                                      'gid': old.st_gid if old else os.getgid()})
        def save():
            atomic(backup / 'manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
        save()
        applied = []
        try:
            for entry, (path, data) in zip(manifest['files'], changes):
                parent = path.parent
                absent = []
                while not parent.exists() and parent != self.root:
                    if parent == self.path('/etc/sddm.conf.d') or parent == self.path(THEME_DIR) or parent.is_relative_to(self.path(THEME_DIR)):
                        absent.append(str(parent))
                    parent = parent.parent
                for name in reversed(absent):
                    if name not in manifest['directories']:
                        manifest['directories'].append(name)
                    Path(name).mkdir(parents=True, exist_ok=True, mode=0o755)
                    Path(name).chmod(0o755)
                mode = entry['mode'] if path.is_relative_to(self.path('/etc')) else 0o644
                atomic(path, data, mode)
                applied.append(entry)
                save()
            if self.effective_theme() != (THEME, '/usr/share/sddm/themes'):
                raise ValueError('A higher-priority SDDM setting prevents Hyprixe theme selection')
            if self.configuration().get('General', 'InputMethod', fallback=None) != '':
                raise ValueError('A higher-priority SDDM setting prevents InputMethod from being disabled')
        except BaseException:
            manifest['files'] = applied
            save()
            self.restore(identifier)
            raise
        (backup / 'complete').touch()
        print(f'SDDM theme installed. System backup: {backup}', file=sys.stderr)
        return identifier

    def read(self, identifier):
        if not re.fullmatch(r'\d{8}T\d{6}\.\d{6}Z-sddm-[0-9a-f]{8}', identifier):
            raise ValueError('Use an SDDM backup ID from --list')
        backup = self.path(BACKUPS) / identifier
        self.guard_state(backup / 'manifest.json')
        manifest = json.loads((backup / 'manifest.json').read_text())
        if (manifest.get('format') != 1 or manifest.get('kind') != 'sddm' or
                manifest.get('id') != identifier or manifest.get('root') != str(self.root)):
            raise ValueError('Invalid SDDM backup manifest')
        if self.actor_uid not in (0, manifest.get('actor_uid')):
            raise ValueError('This SDDM backup belongs to another installing user')
        return backup, manifest

    def list_backups(self):
        result = []
        for path in sorted(self.path(BACKUPS).glob('*'), reverse=True):
            if (path / 'manifest.json').is_file():
                try:
                    _, manifest = self.read(path.name)
                    result.append((path.name, manifest.get('restored', False)))
                except ValueError:
                    continue
        return result

    def restore(self, identifier, dry=False):
        backup, manifest = self.read(identifier)
        if manifest.get('restored'):
            return
        for entry in manifest['files']:
            path = Path(entry['target'])
            self.guard(path)
            if digest(path) not in (entry['before'], entry['after']):
                raise ValueError(f'SDDM file changed since installation; save your edits first. Nothing restored: {path}')
            if entry['backup'] is not None:
                name = entry['backup']
                self.guard_state(backup / 'files' / str(name))
                if not str(name).isdigit() or digest(backup / 'files' / name) != entry['before']:
                    raise ValueError(f'Missing/corrupt SDDM backup file: {name}')
        for name in manifest['directories']:
            self.guard(Path(name), directory=True)
        for entry in reversed(manifest['files']):
            path = Path(entry['target'])
            print('SDDM RESTORE', path, file=sys.stderr)
            if dry:
                continue
            if entry['backup'] is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, (backup / 'files' / entry['backup']).read_bytes(), entry['mode'])
                if os.geteuid() == 0:
                    os.chown(path, entry['uid'], entry['gid'])
        if not dry:
            manifest['restored'] = True
            atomic(backup / 'manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
            for name in reversed(manifest['directories']):
                path = Path(name)
                self.guard(path, directory=True)
                try:
                    path.rmdir()
                except OSError:
                    pass

    def check_installed(self):
        failures = []
        for absolute, data in source_payload(self.repo).items():
            path = self.path(absolute)
            try:
                self.guard(path)
            except ValueError as exc:
                failures.append(str(exc))
                continue
            if not path.is_file() or path.is_symlink() or path.read_bytes() != data:
                failures.append(f'Missing/changed SDDM file: {absolute}')
            elif path.stat().st_mode & 0o444 != 0o444:
                failures.append(f'SDDM theme file is not readable by the greeter: {absolute}')
            if any(p.exists() and p.stat().st_mode & 0o001 == 0 for p in path.parents if p != self.root):
                failures.append(f'SDDM theme parent directory is not traversable by the greeter: {absolute}')
        if self.effective_theme() != (THEME, '/usr/share/sddm/themes'):
            failures.append('Effective SDDM configuration does not select hyprixe-frosted from /usr/share/sddm/themes')
        if not self.path(CONFIG).is_file():
            failures.append(f'Missing dedicated SDDM configuration: {CONFIG}')
        if self.configuration().get('General', 'InputMethod', fallback=None) != '':
            failures.append('Effective SDDM [General] InputMethod must be explicitly empty (virtual keyboard disabled)')
        problem = session_error(self.path(SESSION))
        if problem:
            failures.append(problem)
        directories = self.configuration().get('Wayland', 'SessionDir', fallback='/usr/local/share/wayland-sessions,/usr/share/wayland-sessions')
        if '/usr/share/wayland-sessions' not in [item.strip().rstrip('/') for item in directories.split(',')]:
            failures.append('SDDM [Wayland] SessionDir excludes the Debian UWSM session directory')
        return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'restore', 'check', 'prerequisites'))
    parser.add_argument('--backup')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.action == 'prerequisites':
        prerequisites()
        return
    theme = SystemTheme(actor_uid=int(os.environ.get('SUDO_UID', os.getuid())))
    if args.action == 'check':
        failures = theme.check_installed()
        for failure in failures:
            print('FAIL:', failure)
        if failures:
            raise ValueError('SDDM installation validation failed')
        print('PASS: installed SDDM theme, exact wallpaper, disabled InputMethod and UWSM session entry')
        return
    if args.action == 'install' and args.dry_run:
        theme.install(dry=True)
        return
    if os.geteuid() != 0:
        raise ValueError('Only SDDM system installation/restoration requires sudo')
    state = theme.path('/var/lib/hyprixe/sddm')
    theme.guard_state(state / 'deployment.lock')
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    state.chmod(0o700)
    with (state / 'deployment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == 'install':
            prerequisites()
            print(json.dumps({'backup': theme.install()}))
        else:
            available = theme.list_backups()
            if args.list:
                for identifier, restored in available:
                    print(identifier, 'restored' if restored else 'available')
                return
            identifier = args.backup or next((name for name, restored in available if not restored), None)
            if not identifier:
                raise ValueError('No unrestored SDDM backup found')
            theme.restore(identifier, dry=args.dry_run)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, configparser.Error) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
