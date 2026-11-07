"""Canonical repository sources and stable Debian destination mappings.

Legacy logical names describe the v1 deployment contract, not duplicate files.
There is no fallback to the removed root-level configuration tree.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = 'profiles/debian/install'
BACKEND_FILES = ('deploy.py', 'dolphin_config.py', 'dolphin_interface.py',
                 'interactive_shell.py', 'sddm_theme.py', 'check-deps.py',
                 'build-runtime.sh', 'apt-build-deps.py')
COMPAT_FILES = ('waybar_compat.py', 'rofi_compat.py', 'rofi_launcher.py', 'waybar-lua-ipc.hpp')
PREFIXES = {
    '.config': 'common/config', '.local': 'common/local',
    '.zshrc': 'common/shell/.zshrc', '.p10k.zsh': 'common/shell/.p10k.zsh',
    'wallpapers': 'common/wallpapers', 'sddm': 'common/sddm',
    'dolphin': 'common/metadata/dolphin',
    'profiles/native/profile.lua': 'common/config/hypr/profile.lua',
    'profiles/native/profile.env': 'common/config/hypr/profile.env',
    'profiles/vmware': 'common/hardware/vmware',
    'profiles/vmware/packages.txt': 'profiles/debian/packages/vmware.txt',
    '.config/hypr/scripts/Polkit.sh': 'profiles/debian/config/hypr/scripts/Polkit.sh',
    '.config/systemd/user/hypridle.service.d/hyprixe.conf':
        'profiles/debian/config/systemd/user/hypridle.service.d/hyprixe.conf',
    'scripts/shell_assets.py': 'common/tools/shell_assets.py',
    'scripts/shell-sources.json': 'common/assets/shell-sources.json',
    **{'scripts/' + name: BACKEND + '/' + name for name in BACKEND_FILES},
    **{'scripts/' + name: 'common/compat/' + name for name in COMPAT_FILES},
    **{name: 'profiles/debian/packages/' + name for name in
       ('packages.txt', 'packages-backports.txt', 'packages-dolphin.txt',
        'packages-optional.txt', 'packages-sddm.txt')},
}
# Source prefix -> destination namespace/prefix. The destination contract is v1.
USER_MAPPINGS = (('common/config', 'config', ''),
                 ('common/local/share', 'data', ''),
                 ('common/local/bin', 'home', '.local/bin'),
                 ('common/shell', 'home', ''),
                 ('common/wallpapers', 'data', 'hyprixe/wallpapers'),
                 ('common/theme', 'data', 'hyprixe/theme'))
WALLPAPER_MANIFEST = 'common/assets/wallpapers.json'


def shipping_wallpapers(root=ROOT):
    """Return only reviewed shipping images; reject undeclared source files.

    The manifest is build/deployment metadata, never a runtime wallpaper choice.
    Test images belong under tests/, outside every deployment source prefix.
    """
    root = Path(root)
    directory = root / 'common/wallpapers'
    manifest = json.loads((root / WALLPAPER_MANIFEST).read_text(encoding='utf-8'))
    if (not isinstance(manifest, dict) or set(manifest) != {'format', 'files'} or
            type(manifest['format']) is not int or manifest['format'] != 1 or
            not isinstance(manifest['files'], list) or not manifest['files']):
        raise ValueError('Invalid shipping wallpaper manifest')
    if directory.is_symlink():
        raise ValueError('Shipping wallpaper directory cannot be a symlink')
    declared = {}
    for entry in manifest['files']:
        if not isinstance(entry, dict) or set(entry) != {'file', 'sha256'}:
            raise ValueError('Invalid shipping wallpaper entry')
        name, digest = entry['file'], entry['sha256']
        if (not isinstance(name, str) or not name or name != Path(name).name or
                any(c in name for c in '/\\\r\n\0') or '..' in name or
                Path(name).suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp') or
                not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise ValueError('Invalid shipping wallpaper name/hash')
        if name in declared:
            raise ValueError('Duplicate shipping wallpaper: ' + name)
        declared[name] = directory / name
        if declared[name].is_symlink() or not declared[name].is_file():
            raise ValueError('Missing/unsafe shipping wallpaper: ' + name)
        if hashlib.sha256(declared[name].read_bytes()).hexdigest() != digest:
            raise ValueError('Shipping wallpaper checksum mismatch: ' + name)
    if 'min_forest.jpg' not in declared:
        raise ValueError('Shipping wallpapers must include the default min_forest.jpg')
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*')
              if p.is_file() or p.is_symlink()}
    if actual != set(declared):
        raise ValueError('Undeclared wallpaper files: ' + ', '.join(sorted(actual - set(declared))))
    return tuple(declared[name] for name in sorted(declared))


def source_path(root, relative):
    name = Path(relative).as_posix()
    for prefix in sorted(PREFIXES, key=len, reverse=True):
        if name == prefix or name.startswith(prefix + '/'):
            return Path(root) / PREFIXES[prefix] / name[len(prefix):].lstrip('/')
    return Path(root) / name


def configure_imports():
    paths = [str(ROOT / path) for path in ('scripts', 'common/tools', 'common/compat', 'common/theme', BACKEND)]
    for path in reversed(paths):
        if path not in sys.path:
            sys.path.insert(0, path)
    inherited = os.environ.get('PYTHONPATH', '').split(os.pathsep)
    os.environ['PYTHONPATH'] = os.pathsep.join(dict.fromkeys(paths + [p for p in inherited if p]))


def profile_metadata(name):
    if name not in ('debian', 'nixos'):
        raise ValueError('Unknown platform profile: ' + name)
    return json.loads((ROOT / 'profiles' / name / 'profile.json').read_text())


def detect_profile(os_release=Path('/etc/os-release')):
    try:
        values = dict(line.split('=', 1) for line in os_release.read_text().splitlines()
                      if '=' in line and not line.startswith('#'))
    except OSError:
        return None
    values = {k: v.strip('"\'') for k, v in values.items()}
    if values.get('ID') == 'debian' and values.get('VERSION_ID') == '13':
        return 'debian'
    if values.get('ID') == 'nixos':
        return 'nixos'
    return None


def shell_bytes(root, name, platform='debian'):
    data = source_path(root, name).read_bytes()
    if name == '.zshrc':
        for token, value in profile_metadata(platform)['zsh_plugins'].items():
            data = data.replace(('@' + token + '@').encode(), value.encode())
    return data


def mapped_files(root=ROOT, platform='debian'):
    """Yield canonical source, destination root and destination-relative path."""
    for prefix, namespace, destination in USER_MAPPINGS:
        directory = Path(root) / prefix
        paths = shipping_wallpapers(root) if prefix == 'common/wallpapers' else sorted(directory.rglob('*'))
        for path in paths:
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                yield path, namespace, Path(destination) / path.relative_to(directory)
    integration = Path(root) / 'profiles' / platform / 'config'
    for path in sorted(integration.rglob('*')):
        if path.is_file():
            yield path, 'config', path.relative_to(integration)
    helpers = Path(root) / 'profiles' / platform / 'local/bin'
    for path in sorted(helpers.glob('*')):
        if path.is_file():
            yield path, 'home', Path('.local/bin') / path.name
