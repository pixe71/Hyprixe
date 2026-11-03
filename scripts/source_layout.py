"""Canonical repository sources and stable Debian destination mappings.

Legacy logical names describe the v1 deployment contract, not duplicate files.
There is no fallback to the removed root-level configuration tree.
"""
import json
import os
from pathlib import Path
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
                 ('common/wallpapers', 'data', 'hyprixe/wallpapers'))


def source_path(root, relative):
    name = Path(relative).as_posix()
    for prefix in sorted(PREFIXES, key=len, reverse=True):
        if name == prefix or name.startswith(prefix + '/'):
            return Path(root) / PREFIXES[prefix] / name[len(prefix):].lstrip('/')
    return Path(root) / name


def configure_imports():
    paths = [str(ROOT / path) for path in ('scripts', 'common/tools', 'common/compat', BACKEND)]
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
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                yield path, namespace, Path(destination) / path.relative_to(directory)
    integration = Path(root) / 'profiles' / platform / 'config'
    for path in sorted(integration.rglob('*')):
        if path.is_file():
            yield path, 'config', path.relative_to(integration)
