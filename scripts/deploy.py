"""File-level deployment with durable backups, conflict detection and rollback.

All modifications stay below HOME. Directories/symlinks owned by another setup
are refused rather than followed. The manifest records every file, including
merged MIME/KDE/Qt settings, so restore never recursively deletes config dirs.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]


def digest(path):
    if path.is_symlink():
        return 'link:' + os.readlink(path)
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if path.exists():
        return 'directory'
    return None


def atomic(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.hyprixe-' + uuid.uuid4().hex)
    try:
        tmp.write_bytes(data)
        tmp.chmod(mode)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def locations():
    home = Path(os.environ['HOME']).absolute()
    if home.is_symlink() or home.resolve() != home:
        raise ValueError('HOME must be an absolute canonical path')
    roots = {'config': Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')),
             'data': Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')),
             'state': Path(os.environ.get('XDG_STATE_HOME', home / '.local/state'))}
    for name, path in roots.items():
        if not path.is_absolute() or not path.is_relative_to(home) or path == home:
            raise ValueError(f'XDG {name} must be an absolute subdirectory of HOME: {path}')
        # Reject traversal in XDG overrides before normalisation.
        if '..' in path.parts or any(c in str(path) for c in '\n\r\0'):
            raise ValueError(f'Unsupported XDG path: {path}')
    return home, roots


def guard(path, home, parents_only=False):
    if not path.is_absolute() or not path.is_relative_to(home) or path == home or '..' in path.parts:
        raise ValueError(f'Unsafe target: {path}')
    for parent in path.parents:
        if parent == home:
            break
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise ValueError(f'Parent is a symlink or not a directory: {parent}')
    if not parents_only and path.exists() and path.is_dir():
        raise ValueError(f'Expected a file, found a directory: {path}')


def merge_ini(old, updates):
    # Preserve unrelated groups and comments (KConfig uses nested [A][B] groups).
    lines = old.splitlines(keepends=True)
    for group, values in updates.items():
        header = f'[{group}]'
        start = next((i for i, line in enumerate(lines) if line.strip() == header), None)
        if start is None:
            lines.extend(['\n', header + '\n'])
            start = len(lines) - 1
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('[')), len(lines))
        block = lines[start + 1:end]
        trailing = []
        while block and not block[-1].strip():
            trailing.insert(0, block.pop())
        for key, value in values.items():
            block = [line for line in block if line.split('=', 1)[0].strip() != key]
            block.append(f'{key}={value}\n')
        lines[start + 1:end] = block + trailing
    return ''.join(lines)


def payload(roots, profile, runtime=None):
    result = {}
    for p in sorted((REPO / '.config').rglob('*')):
        if p.is_file():
            result[roots['config'] / p.relative_to(REPO / '.config')] = (p.read_bytes(), 0o755 if p.suffix == '.sh' else 0o644)
    for p in sorted((REPO / '.local/share').rglob('*')):
        if p.is_file():
            result[roots['data'] / p.relative_to(REPO / '.local/share')] = (p.read_bytes(), 0o644)
    result[roots['data'] / 'hyprixe/wallpapers/min_forest.jpg'] = ((REPO / 'wallpapers/min_forest.jpg').read_bytes(), 0o644)
    hypr = roots['config'] / 'hypr'
    local_waybar = Path(os.environ['HOME']) / '.local/bin/waybar'
    staged_waybar = runtime and (Path(runtime) / 'waybar').is_file()
    waybar = str(local_waybar if staged_waybar or local_waybar.is_file() else shutil.which('waybar') or '/usr/bin/waybar')
    for name in ('profile.lua', 'profile.env'):
        result[hypr / name] = ((REPO / 'profiles' / profile / name).read_bytes(), 0o644)
    # Render application paths once; session scripts themselves honour XDG variables.
    for target, (data, mode) in list(result.items()):
        if target.suffix in ('.rasi', '.conf') or target == hypr / 'waybar/config':
            text = data.decode('utf-8')
            text = text.replace('~/.config/hypr', str(hypr))
            text = text.replace('$HOME/.config/hypr', str(hypr))
            text = text.replace('$HOME/.local/share/hyprixe', str(roots['data'] / 'hyprixe'))
            unit_path = str(hypr).replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"')
            text = text.replace('@HYPR_CONFIG@', unit_path)
            text = text.replace('@WAYBAR_EXEC@', waybar.replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"'))
            # Waybar wrapper is JSON; escape paths containing quotes/backslashes.
            if target == hypr / 'waybar/config':
                text = json.dumps({'include': [str(hypr / 'waybar/configs/Frosted-Glass')]}) + '\n'
            result[target] = (text.encode(), mode)
    # Set directory MIME default while preserving all other associations.
    result[roots['config'] / 'mimeapps.list'] = (b'', 0o644)
    merged = {
        'mimeapps.list': {'Default Applications': {'inode/directory': 'org.kde.dolphin.desktop;'}},
        'hyprland-mimeapps.list': {'Default Applications': {'inode/directory': 'org.kde.dolphin.desktop;'}},
        'kdeglobals': {'General': {'TerminalApplication': 'alacritty', 'TerminalService': 'Alacritty.desktop'}, 'Icons': {'Theme': 'breeze-dark'}, 'KDE': {'widgetStyle': 'kvantum'}},
        'qt6ct/qt6ct.conf': {'Appearance': {'style': 'kvantum', 'icon_theme': 'breeze-dark'}},
    }
    for name, values in merged.items():
        target = roots['config'] / name
        old = target.read_text() if target.is_file() else ''
        result[target] = (merge_ini(old, values).encode(), 0o644)
    # A stale legacy entrypoint may take precedence over Lua. Back it up and remove it.
    result[hypr / 'hyprland.conf'] = (None, None)
    if runtime:
        for name in ('rofi', 'awww', 'awww-daemon', 'waybar'):
            source = Path(runtime) / name
            if source.is_file():
                result[Path(os.environ['HOME']) / '.local/bin' / name] = (source.read_bytes(), 0o755)
    return result


def read_manifest(path):
    data = json.loads((path / 'manifest.json').read_text())
    if data.get('format') != 1 or data.get('id') != path.name:
        raise ValueError(f'Invalid backup manifest: {path}')
    return data


def restore(backup, home, dry=False, rollback=False):
    manifest = read_manifest(backup)
    if manifest.get('home') != str(home):
        raise ValueError('Backup belongs to a different HOME')
    if manifest.get('restored'):
        raise ValueError('This backup has already been restored')
    entries = manifest['files']
    conflicts = []
    for entry in entries:
        p = Path(entry['target'])
        guard(p, home)
        current = digest(p)
        if current not in (entry['after'], entry['before']):
            conflicts.append(str(p))
        saved = entry.get('backup')
        if saved is not None:
            source = backup / 'files' / saved
            if Path(saved).name != saved or saved in ('.', '..') or digest(source) != entry['before']:
                raise ValueError(f'Backup is missing or corrupt: {saved}')
    if conflicts:
        raise ValueError('Files changed since installation; save your edits first. Nothing restored:\n' + '\n'.join(conflicts))
    for entry in reversed(entries):
        target = Path(entry['target'])
        print('RESTORE', target)
        if dry:
            continue
        if digest(target) == entry['before'] and (not target.is_file() or target.is_symlink()
                or stat.S_IMODE(target.stat().st_mode) == entry['mode']):
            continue
        saved = entry.get('backup')
        if saved is None:
            target.unlink(missing_ok=True)
        else:
            source = backup / 'files' / saved
            if not source.is_relative_to(backup / 'files') or '..' in Path(saved).parts:
                raise ValueError('Invalid backup path')
            if source.is_symlink():
                target.unlink(missing_ok=True)
                target.symlink_to(os.readlink(source))
            else:
                atomic(target, source.read_bytes(), entry['mode'])
    if not dry:
        manifest['restored'] = True
        atomic(backup / 'manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
        # Only empty directories created by this transaction can be removed.
        for name in reversed(manifest.get('directories', [])):
            p = Path(name)
            guard(p, home, parents_only=True)
            try:
                p.rmdir()
            except OSError:
                pass
        (backup / ('rolled-back' if rollback else 'restored')).touch()


def install(home, roots, profile, dry=False, runtime=None):
    # Refuse symlinked parents even during preview, before reading merge targets.
    for root in roots.values():
        guard(root / '.hyprixe-path-check', home)
    content = payload(roots, profile, runtime)
    changes = []
    for path, (data, mode) in content.items():
        guard(path, home)
        before = digest(path)
        after = hashlib.sha256(data).hexdigest() if data is not None else None
        # Symlinks are replaced/backed up, even when they point at identical content.
        if before == after and (data is None or stat.S_IMODE(path.stat().st_mode) == mode):
            continue
        changes.append((path, data, mode))
    print(f'Profile {profile}: {len(changes)} files to change')
    if dry:
        for p, data, _ in changes:
            print('REMOVE (backed up)' if data is None else 'INSTALL (backed up)', p)
        return
    if not changes:
        print('Already up to date; no additional backup created.')
        return
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + profile
    backup = roots['state'] / 'hyprixe/backups' / identifier
    backup.mkdir(parents=True, mode=0o700)
    manifest = {'format': 1, 'id': identifier, 'home': str(home), 'profile': profile, 'files': [], 'directories': []}
    # Back up EVERY target before the first mutation.
    for i, (target, data, mode) in enumerate(changes):
        old = digest(target)
        saved = str(i) if old is not None else None
        oldmode = stat.S_IMODE(target.lstat().st_mode) if old is not None else None
        if saved is not None:
            dst = backup / 'files' / saved
            dst.parent.mkdir(exist_ok=True)
            shutil.copy2(target, dst, follow_symlinks=False)
        manifest['files'].append({'target': str(target), 'backup': saved, 'mode': oldmode,
                                  'before': old, 'after': hashlib.sha256(data).hexdigest() if data is not None else None})
    def save():
        atomic(backup / 'manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
    save()
    applied = []
    try:
        for entry, (target, data, mode) in zip(manifest['files'], changes):
            absent = []
            parent = target.parent
            while not parent.exists():
                absent.append(str(parent))
                parent = parent.parent
            for name in reversed(absent):
                if name not in manifest['directories']:
                    manifest['directories'].append(name)
            if data is None:
                target.unlink(missing_ok=True)
            else:
                atomic(target, data, mode)
            applied.append(entry)
            save()
            print('INSTALLED', target)
    except BaseException:
        # Roll back only successful writes; never overwrite the failing target.
        manifest['files'] = applied
        save()
        restore(backup, home, rollback=True)
        raise
    (backup / 'complete').touch()
    print('Backup:', backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    ins = sub.add_parser('install')
    ins.add_argument('--profile', choices=['native', 'vmware'], default='native')
    ins.add_argument('--dry-run', action='store_true')
    ins.add_argument('--runtime', help='Internal: directory containing staged runtime binaries')
    res = sub.add_parser('restore')
    res.add_argument('--backup', help='Backup ID (default: most recent unrestored transaction)')
    res.add_argument('--list', action='store_true')
    res.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    home, roots = locations()
    state = roots['state'] / 'hyprixe'
    guard(state / 'deployment.lock', home)
    if args.action == 'install' and args.dry_run:
        install(home, roots, args.profile, dry=True, runtime=args.runtime)
        return
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'deployment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == 'install':
            install(home, roots, args.profile, runtime=args.runtime)
        else:
            backups = sorted((state / 'backups').glob('*'), reverse=True)
            backups = [p for p in backups if (p / 'manifest.json').is_file()]
            for p in backups:
                guard(p / 'manifest.json', home)
            if args.list:
                for p in backups:
                    m = read_manifest(p)
                    print(p.name, 'restored' if m.get('restored') else 'available')
                return
            available = [p for p in backups if not read_manifest(p).get('restored')]
            if args.backup:
                if Path(args.backup).name != args.backup or args.backup in ('.', '..'):
                    raise ValueError('Use a backup ID from --list')
                backup = state / 'backups' / args.backup
            elif available:
                backup = available[0]
            else:
                raise ValueError('No unrestored backup found')
            restore(backup, home, dry=args.dry_run)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
