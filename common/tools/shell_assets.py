"""Stage pinned, checksummed upstream prompt/font files; never change a login shell."""

from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "scripts"))
from source_layout import ROOT as REPOSITORY_ROOT, source_path, configure_imports, shell_bytes
configure_imports()
import argparse
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request

PINS = json.loads(source_path(REPOSITORY_ROOT, 'scripts/shell-sources.json').read_text())
STAMP = 'hyprixe-source.json'
FONT = 'SymbolsNerdFontMono-Regular.ttf'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def machine():
    value = platform.machine().lower()
    return {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(value, value)


def download(pin, cache, offline=False):
    path = cache / pin['sha256']
    if path.is_file() and sha(path.read_bytes()) == pin['sha256']:
        return path.read_bytes()
    if offline:
        raise ValueError('Pinned shell asset is unavailable offline; run ./install.sh native without --no-packages')
    print('Downloading verified shell asset:', pin['url'], flush=True)
    with urllib.request.urlopen(pin['url'], timeout=60) as response:
        data = response.read()
    if sha(data) != pin['sha256']:
        raise ValueError('SHA256 mismatch: ' + pin['url'])
    cache.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def extract(data, target, strip_root=False):
    """Only regular files/directories; no traversal, links or special devices."""
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        members = archive.getmembers()
        roots = {Path(m.name).parts[0] for m in members if Path(m.name).parts}
        if strip_root and len(roots) != 1:
            raise ValueError('Unexpected upstream archive root')
        for member in members:
            name = Path(member.name)
            if name.is_absolute() or '..' in name.parts or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe upstream archive member: ' + member.name)
        for member in members:
            parts = Path(member.name).parts[1:] if strip_root else Path(member.name).parts
            if not parts:
                continue
            path = target.joinpath(*parts)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.extractfile(member).read())
                path.chmod(0o755 if member.mode & 0o111 else 0o644)


def gitstatus_pin(folder):
    # The exact install.info is authenticated by the pinned P10k archive hash.
    # Parse assignments as data, not the upstream installer's shell eval/mirrors.
    for line in (folder / 'gitstatus/install.info').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        fields = dict(word.split('=', 1) for word in shlex.split(line.replace(';', ' ')))
        if fnmatch.fnmatch('linux', fields['uname_s_glob']) and fnmatch.fnmatch(machine(), fields['uname_m_glob']):
            name = fields['file'].replace('${uname_s}', 'linux').replace('${uname_m}', machine())
            if (not re.fullmatch(r'gitstatusd-linux-[a-z0-9_]+', name)
                    or not re.fullmatch(r'v[0-9.]+', fields['version'])
                    or not re.fullmatch(r'[0-9a-f]{64}', fields['sha256'])):
                raise ValueError('Unsupported gitstatus archive name/version')
            return {'url': f'https://github.com/romkatv/gitstatus/releases/download/{fields["version"]}/{name}.tar.gz',
                    'sha256': fields['sha256'], 'file': name, 'version': fields['version']}
    raise ValueError('No official prebuilt gitstatus binary for Linux ' + machine())


def tree_manifest(folder):
    files = {}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError('Prompt assets must not contain symlinks')
        if path.is_file() and path.name != STAMP:
            files[str(path.relative_to(folder))] = {'sha256': sha(path.read_bytes()), 'mode': stat.S_IMODE(path.stat().st_mode)}
    return {'format': 1, 'commit': PINS['powerlevel10k']['commit'], 'machine': machine(), 'files': files}


def validate(folder):
    record = json.loads((folder / STAMP).read_text())
    if not isinstance(record, dict) or record.get('format') != 1 or record.get('commit') != PINS['powerlevel10k']['commit'] or record.get('machine') != machine():
        raise ValueError('Powerlevel10k pin/architecture differs from Hyprixe')
    files = record.get('files')
    if not isinstance(files, dict):
        raise ValueError('Invalid Powerlevel10k file manifest')
    for name in ('powerlevel10k.zsh-theme', 'internal/p10k.zsh', 'LICENSE', 'gitstatus/install.info'):
        if name not in files:
            raise ValueError('Powerlevel10k manifest omits ' + name)
    for name, expected in files.items():
        if (not isinstance(name, str) or not isinstance(expected, dict)
                or not re.fullmatch(r'[0-9a-f]{64}', str(expected.get('sha256', '')))
                or expected.get('mode') not in (0o644, 0o755)):
            raise ValueError('Invalid Powerlevel10k file record')
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe Powerlevel10k manifest path')
        path = folder / relative
        if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()) or sha(path.read_bytes()) != expected['sha256']:
            raise ValueError('Powerlevel10k file is missing/changed: ' + name)
        if stat.S_IMODE(path.stat().st_mode) != expected['mode']:
            raise ValueError('Powerlevel10k file mode changed: ' + name)
    pin = gitstatus_pin(folder)
    daemon = folder / 'gitstatus/usrbin' / pin['file']
    if str(daemon.relative_to(folder)) not in files or not os.access(daemon, os.X_OK):
        raise ValueError('Prepared gitstatus daemon is missing/non-executable')
    return record


def check_daemon(folder):
    pin = gitstatus_pin(folder)
    result = subprocess.run([str(folder / 'gitstatus/usrbin' / pin['file']), '--version'],
                            capture_output=True, text=True, timeout=15, check=True)
    if pin['version'] not in result.stdout:
        raise ValueError('Prepared gitstatus binary has an unexpected version')


def prepare(output, home, data, offline=False):
    cache = Path(os.environ.get('XDG_CACHE_HOME', home / '.cache')) / 'hyprixe/shell-sources'
    existing = data / 'hyprixe/powerlevel10k'
    target = output / 'powerlevel10k'
    try:
        record = validate(existing)
    except (OSError, ValueError, KeyError):
        record = None
    if record:
        print('Reusing verified Powerlevel10k ' + PINS['powerlevel10k']['tag'])
        for name in (*record['files'], STAMP):
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(existing / name, path)
    else:
        extract(download(PINS['powerlevel10k'], cache, offline), target, strip_root=True)
        pin = gitstatus_pin(target)
        extract(download(pin, cache, offline), target / 'gitstatus/usrbin')
        daemon = target / 'gitstatus/usrbin' / pin['file']
        daemon.chmod(0o755)
        (target / STAMP).write_text(json.dumps(tree_manifest(target), indent=2) + '\n')
    validate(target)
    check_daemon(target)
    for key, name in (('symbols', FONT), ('symbols_license', 'LICENSE')):
        installed = data / 'fonts/hyprixe-symbols' / name
        value = installed.read_bytes() if installed.is_file() else b''
        if sha(value) != PINS[key]['sha256']:
            value = download(PINS[key], cache, offline)
        path = output / 'shell-fonts' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        path.chmod(0o644)


def payload(home, data, runtime):
    if not runtime or not (Path(runtime) / 'powerlevel10k').is_dir():
        return {}
    folder = Path(runtime) / 'powerlevel10k'
    record = validate(folder)
    files = {data / 'hyprixe/powerlevel10k' / name: ((folder / name).read_bytes(), entry['mode'])
             for name, entry in record['files'].items()}
    files[data / 'hyprixe/powerlevel10k' / STAMP] = ((folder / STAMP).read_bytes(), 0o644)
    for key, name in (('symbols', FONT), ('symbols_license', 'LICENSE')):
        value = (Path(runtime) / 'shell-fonts' / name).read_bytes()
        if sha(value) != PINS[key]['sha256']:
            raise ValueError('Invalid staged Nerd Font asset: ' + name)
        files[data / 'fonts/hyprixe-symbols' / name] = (value, 0o644)
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    try:
        home = Path.home()
        prepare(args.runtime, home, Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')), args.offline)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        sys.exit('ERROR: shell preparation: ' + str(exc))
