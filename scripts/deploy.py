"""File-level deployment with durable backups, conflict detection and rollback.

All modifications stay below HOME. Directories/symlinks owned by another setup
are refused rather than followed. The manifest records every file, including
merged MIME/KDE/Qt settings, so restore never recursively deletes config dirs.
"""
import argparse
import base64
import configparser
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import uuid
import dolphin_config
from wlogout_checks import validate as validate_wlogout

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


def payload(roots, profile, runtime=None, dolphin_only=False, waybar_only=False):
    if waybar_only:
        result = {}
        # Explicit source list: missing active assets fail before any write;
        # caches and unrelated files can never enter the deployment.
        for name in ('configs/Frosted-Glass', 'style.css', 'style/Frosted-Glass.css', 'scripts/temperature.py'):
            source = REPO / '.config/hypr/waybar' / name
            result[roots['config'] / 'hypr/waybar' / name] = (source.read_bytes(), 0o644)
        for name in ('HyprixeDebian.ttf', 'LICENSE.txt', 'README.md'):
            source = REPO / '.local/share/fonts/hyprixe' / name
            result[roots['data'] / 'fonts/hyprixe' / name] = (source.read_bytes(), 0o644)
        return result
    if dolphin_only:
        return dolphin_config.payload(REPO, roots, merge_ini)
    for relative in ('configs/Frosted-Glass', 'style.css', 'style/Frosted-Glass.css'):
        source = REPO / '.config/hypr/waybar' / relative
        if not source.is_file():
            raise FileNotFoundError(f'Required Waybar file missing: {source}')
    if not (REPO / '.config/kitty/kitty.conf').is_file():
        raise FileNotFoundError('Required Kitty configuration missing: .config/kitty/kitty.conf')
    validate_wlogout(REPO / '.config')
    result = {}
    launcher = REPO / '.local/bin/hyprixe-session'
    result[Path(os.environ['HOME']) / '.local/bin/hyprixe-session'] = (launcher.read_bytes(), 0o755)
    for p in sorted((REPO / '.config').rglob('*')):
        if p.is_file():
            if p.relative_to(REPO / '.config') == Path('dolphinrc') and (roots['config'] / 'dolphinrc').exists():
                continue  # Existing interface belongs to the user, not the paint theme.
            result[roots['config'] / p.relative_to(REPO / '.config')] = (p.read_bytes(), 0o755 if p.suffix == '.sh' else 0o644)
    for p in sorted((REPO / '.local/share').rglob('*')):
        if p.is_file():
            if p.relative_to(REPO / '.local/share') == Path('kxmlgui5/dolphin/dolphinui.rc') and (roots['data'] / 'kxmlgui5/dolphin/dolphinui.rc').exists():
                continue
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
        if target.suffix in ('.rasi', '.conf', '.service', '.target'):
            text = data.decode('utf-8')
            text = text.replace('~/.config/hypr', str(hypr))
            text = text.replace('$HOME/.config/hypr', str(hypr))
            text = text.replace('$HOME/.local/share/hyprixe', str(roots['data'] / 'hyprixe'))
            unit_path = str(hypr).replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"')
            text = text.replace('@HYPR_CONFIG@', unit_path)
            text = text.replace('@WAYBAR_EXEC@', waybar.replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"'))
            result[target] = (text.encode(), mode)
    # Set directory MIME default while preserving all other associations.
    result[roots['config'] / 'mimeapps.list'] = (b'', 0o644)
    merged = {
        'mimeapps.list': {'Default Applications': {'inode/directory': 'org.kde.dolphin.desktop;'}},
        'hyprland-mimeapps.list': {'Default Applications': {'inode/directory': 'org.kde.dolphin.desktop;'}},
        'kdeglobals': {'General': {'TerminalApplication': 'kitty', 'TerminalService': 'kitty.desktop'}, 'Icons': {'Theme': 'breeze-dark'}, 'KDE': {'widgetStyle': 'kvantum'}},
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
    result.update(dolphin_config.payload(REPO, roots, merge_ini, default_theme='Frosted-Glass'))
    return result


def read_manifest(path):
    data = json.loads((path / 'manifest.json').read_text())
    if data.get('format') != 1 or data.get('id') != path.name:
        raise ValueError(f'Invalid backup manifest: {path}')
    return data


def restore(backup, home, dry=False, rollback=False, save_dolphin_changes=False):
    manifest = read_manifest(backup)
    if manifest.get('home') != str(home):
        raise ValueError('Backup belongs to a different HOME')
    if manifest.get('restored'):
        raise ValueError('This backup has already been restored')
    entries = manifest['files']
    conflicts, preserve, selective = [], [], {}
    color = manifest.get('dolphin_color_scheme')
    dolphin_targets = set(manifest.get('dolphin_targets', []))
    for entry in entries:
        p = Path(entry['target'])
        guard(p, home)
        current = digest(p)
        if current not in (entry['after'], entry['before']):
            if color and str(p) == color['path'] and p.is_file() and not p.is_symlink():
                current_color = dolphin_config.read_ini(p).get('UiSettings', 'ColorScheme', fallback=None)
                if current_color not in (color['before'], color['after']):
                    conflicts.append(str(p) + ' (ColorScheme changed)')
                else:
                    text = dolphin_config.remove_key(p.read_text(), 'UiSettings', 'ColorScheme')
                    if color['before'] is not None:
                        text = merge_ini(text, {'UiSettings': {'ColorScheme': color['before']}})
                    selective[p] = text.encode()
            elif save_dolphin_changes and str(p) in dolphin_targets and current != 'directory':
                preserve.append(p)
            else:
                conflicts.append(str(p))
        saved = entry.get('backup')
        if saved is not None:
            source = backup / 'files' / saved
            if Path(saved).name != saved or saved in ('.', '..') or digest(source) != entry['before']:
                raise ValueError(f'Backup is missing or corrupt: {saved}')
    view = manifest.get('dolphin_view_xattr')
    changed_view = None
    if view:
        directory = Path(view['path'])
        if str(directory / '.directory') not in dolphin_targets or view['name'] != dolphin_config.VIEW_XATTR:
            raise ValueError('Invalid Dolphin view-metadata record')
        guard(directory / '.metadata-path-check', home)
        if view['before'] is not None:
            base64.b64decode(view['before'], validate=True)
        current_view = dolphin_config.view_metadata(directory)
        if not current_view['supported'] and view['before'] is not None:
            raise ValueError('Filesystem no longer supports the saved Dolphin view metadata')
        if current_view['value'] not in (view['before'], view.get('after', view['before'])):
            if save_dolphin_changes:
                changed_view = {'path': str(directory), 'name': view['name'], 'value': current_view['value']}
            else:
                conflicts.append(str(directory) + ' (' + view['name'] + ')')
    if conflicts:
        raise ValueError('Files changed since installation; save your edits first. Nothing restored:\n' + '\n'.join(conflicts))
    system_backup = manifest.get('sddm_backup')
    if system_backup:
        # Check both transactions before either is changed. Root restoration is
        # resumable if a later user write fails or power is interrupted.
        system_theme('restore', '--backup', system_backup, '--dry-run')
    if preserve or changed_view:
        print('SAVE current Dolphin changes before restore:', ', '.join(map(str, preserve)))
        if not dry:
            saved = backup / ('preserved-dolphin-' + uuid.uuid4().hex)
            saved.mkdir(mode=0o700)
            records = []
            for i, path in enumerate(preserve):
                record = {'path': str(path), 'sha256_or_link': digest(path), 'saved': None}
                if record['sha256_or_link'] is not None:
                    shutil.copy2(path, saved / str(i), follow_symlinks=False)
                    record['saved'] = str(i)
                records.append(record)
            atomic(saved / 'manifest.json', (json.dumps({'files': records, 'view_xattr': changed_view}, indent=2) + '\n').encode())
            print('Current Dolphin files/metadata preserved in:', saved)
    if system_backup and not dry:
        system_theme('restore', '--backup', system_backup)
    for entry in reversed(entries):
        target = Path(entry['target'])
        print('RESTORE', target)
        if dry:
            continue
        if target in selective:
            # Dolphin saves window preferences on exit. Revert only our color
            # selection while retaining every later interface preference.
            atomic(target, selective[target], stat.S_IMODE(target.stat().st_mode))
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
        if view:
            dolphin_config.restore_view_metadata(Path(view['path']), view['before'])
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


def install(home, roots, profile, dry=False, runtime=None, dolphin_only=False,
            custom_files=None, view_xattr_after=None, scope=None, waybar_only=False):
    # Refuse symlinked parents even during preview, before reading merge targets.
    for root in roots.values():
        guard(root / '.hyprixe-path-check', home)
    content = custom_files if custom_files is not None else payload(roots, profile, runtime, dolphin_only=dolphin_only, waybar_only=waybar_only)
    view_directory = roots['data'] / 'dolphin/view_properties/global'
    if view_xattr_after is not None:
        guard(view_directory / '.metadata-path-check', home)
        view_before = dolphin_config.view_metadata(view_directory)['value']
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
        if view_xattr_after is not None and view_xattr_after['value'] != view_before:
            print('RESTORE (backed up) Dolphin view metadata:', view_directory)
        return
    attribute_changed = view_xattr_after is not None and view_xattr_after['value'] != view_before
    if not changes and not attribute_changed:
        print('Already up to date; no additional backup created.')
        return
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + profile + ('-' + scope if scope else '-dolphin' if dolphin_only else '-waybar' if waybar_only else '')
    backup = roots['state'] / 'hyprixe/backups' / identifier
    backup.mkdir(parents=True, mode=0o700)
    manifest = {'format': 1, 'id': identifier, 'home': str(home), 'profile': profile, 'files': [], 'directories': []}
    manifest['scope'] = scope or ('dolphin-style' if dolphin_only else 'waybar' if waybar_only else 'full')
    if dolphin_only:
        rc = roots['config'] / 'dolphinrc'
        previous = dolphin_config.read_ini(rc).get('UiSettings', 'ColorScheme', fallback=None) if rc.is_file() else None
        manifest['dolphin_color_scheme'] = {'path': str(rc), 'before': previous, 'after': dolphin_config.SCHEME_NAME}
    dolphin_candidates = set(custom_files) if custom_files is not None else {roots['config'] / name for name in dolphin_config.THEME_FILES}
    manifest['dolphin_targets'] = [str(path) for path, _, _ in changes if path in dolphin_candidates]
    if str(view_directory / '.directory') in manifest['dolphin_targets'] or view_xattr_after is not None:
        guard(view_directory / '.metadata-path-check', home)
        metadata = dolphin_config.view_metadata(view_directory)
        manifest['dolphin_view_xattr'] = {'path': str(view_directory), 'name': dolphin_config.VIEW_XATTR,
                                         'before': metadata['value']}
        if view_xattr_after is not None:
            manifest['dolphin_view_xattr']['after'] = view_xattr_after['value']
            if str(view_directory / '.directory') not in manifest['dolphin_targets']:
                manifest['dolphin_targets'].append(str(view_directory / '.directory'))
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
        if view_xattr_after is not None:
            dolphin_config.restore_view_metadata(view_directory, view_xattr_after['value'])
    except BaseException:
        # Roll back only successful writes; never overwrite the failing target.
        manifest['files'] = applied
        save()
        restore(backup, home, rollback=True)
        raise
    (backup / 'complete').touch()
    print('Backup:', backup)
    return backup


def system_theme(action, *arguments):
    command = [sys.executable, str(REPO / 'scripts/sddm_theme.py'), action, *arguments]
    # Preview/check never needs elevated privileges. Only system writes and
    # access to private root backups use sudo.
    if not (action in ('check', 'prerequisites') or
            (action == 'install' and '--dry-run' in arguments)) and os.geteuid() != 0:
        command.insert(0, 'sudo')
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, check=True)
    return result.stdout


def install_with_sddm(home, roots, profile, dry=False, runtime=None):
    if dry:
        install(home, roots, profile, dry=True, runtime=runtime)
        print(system_theme('install', '--dry-run'), end='')
        return
    system_theme('prerequisites')
    backup = install(home, roots, profile, runtime=runtime)
    system_backup = None
    try:
        system_backup = json.loads(system_theme('install'))['backup']
        if not system_backup:
            return backup
        if backup is None:
            # A system-only update still gets an ordinary user restore entry.
            identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + profile
            backup = roots['state'] / 'hyprixe/backups' / identifier
            backup.mkdir(parents=True, mode=0o700)
            manifest = {'format': 1, 'id': identifier, 'home': str(home),
                        'profile': profile, 'files': [], 'directories': []}
        else:
            manifest = read_manifest(backup)
        manifest['sddm_backup'] = system_backup
        atomic(backup / 'manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
        (backup / 'complete').touch()
        print('SDDM system backup linked to user transaction:', backup)
        return backup
    except BaseException:
        if system_backup:
            system_theme('restore', '--backup', system_backup)
        if backup and (backup / 'manifest.json').is_file():
            restore(backup, home, rollback=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    ins = sub.add_parser('install')
    ins.add_argument('--profile', choices=['native', 'vmware'], default='native')
    ins.add_argument('--dry-run', action='store_true')
    ins.add_argument('--runtime', help='Internal: directory containing staged runtime binaries')
    ins.add_argument('--sddm', action='store_true', help='Also deploy the system SDDM theme through sudo')
    ins.add_argument('--dolphin-only', action='store_true', help='Only deploy Dolphin-specific Kvantum paint, association and KDE color selection')
    ins.add_argument('--waybar-only', action='store_true', help='Only deploy Waybar configuration, helper and Debian logo glyph')
    interface = sub.add_parser('restore-dolphin-interface', help='Restore only interface changes introduced by 9259fa5 from an existing backup')
    interface.add_argument('--backup')
    interface.add_argument('--dry-run', action='store_true')
    res = sub.add_parser('restore')
    res.add_argument('--backup', help='Backup ID (default: most recent unrestored transaction)')
    res.add_argument('--list', action='store_true')
    res.add_argument('--dry-run', action='store_true')
    res.add_argument('--save-dolphin-changes', action='store_true', help='Preserve changed Dolphin files/view metadata before restoring their originals')
    args = parser.parse_args()
    if args.action == 'install' and sum((args.dolphin_only, args.waybar_only, args.sddm)) > 1:
        raise ValueError('Component-only installation cannot deploy another component or SDDM')
    home, roots = locations()
    state = roots['state'] / 'hyprixe'
    guard(state / 'deployment.lock', home)
    if args.action == 'restore-dolphin-interface':
        import dolphin_interface
        if not args.dry_run:
            dolphin_config.ensure_closed()
        if args.dry_run:
            files, attribute = dolphin_interface.plan(REPO, roots, home, read_manifest, digest, guard, args.backup)
            install(home, roots, 'native', dry=True, custom_files=files, view_xattr_after=attribute, scope='dolphin-interface')
        else:
            state.mkdir(parents=True, exist_ok=True)
            with (state / 'deployment.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                files, attribute = dolphin_interface.plan(REPO, roots, home, read_manifest, digest, guard, args.backup)
                install(home, roots, 'native', custom_files=files, view_xattr_after=attribute, scope='dolphin-interface')
        return
    if args.action == 'install' and args.dry_run:
        function = install_with_sddm if args.sddm else install
        options = {'dolphin_only': True} if args.dolphin_only else {'waybar_only': True} if args.waybar_only else {}
        function(home, roots, args.profile, dry=True, runtime=args.runtime, **options)
        return
    if args.action == 'install' and not args.waybar_only:
        dolphin_config.ensure_closed()
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'deployment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == 'install':
            function = install_with_sddm if args.sddm else install
            options = {'dolphin_only': True} if args.dolphin_only else {'waybar_only': True} if args.waybar_only else {}
            function(home, roots, args.profile, runtime=args.runtime, **options)
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
            if not args.dry_run and any(Path(e['target']).name in ('dolphinrc', 'dolphinstaterc') for e in read_manifest(backup)['files']):
                dolphin_config.ensure_closed()
            restore(backup, home, dry=args.dry_run, save_dolphin_changes=args.save_dolphin_changes)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, configparser.Error, subprocess.CalledProcessError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
