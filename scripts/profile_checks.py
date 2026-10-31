"""Small platform registry and checks preventing duplicated desktop sources."""
import hashlib
import json
from pathlib import Path


def registry(root):
    result = {}
    for path in sorted((Path(root) / 'profiles').glob('*/profile.json')):
        data = json.loads(path.read_text())
        name = path.parent.name
        if data.get('id') != name or data.get('status') not in ('supported', 'planned'):
            raise ValueError('Invalid platform metadata: ' + str(path))
        if data.get('common_source') != 'common':
            raise ValueError('Profiles must consume common/: ' + name)
        if data['status'] == 'supported':
            backend = Path(root) / data.get('backend', '')
            if not (backend / 'install.sh').is_file() or not data.get('tests'):
                raise ValueError('Supported profile needs a backend and regression tests: ' + name)
            for module in data['tests']:
                if not (Path(root) / 'tests' / (module + '.py')).is_file():
                    raise ValueError('Supported profile test module missing: ' + module)
        result[name] = data
    if not result:
        raise ValueError('No platform profiles registered')
    return result


def duplication_errors(root):
    root = Path(root)
    common = {}
    for path in (root / 'common').rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            common.setdefault(hashlib.sha256(path.read_bytes()).digest(), path)
    errors = []
    for path in (root / 'profiles').rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.name not in ('README.md', 'profile.json'):
            original = common.get(hashlib.sha256(path.read_bytes()).digest())
            if original:
                errors.append(f'{path.relative_to(root)} duplicates {original.relative_to(root)}')
    return errors


def check_sources(report, root):
    try:
        profiles = registry(root)
        errors = duplication_errors(root)
        # Integration files may add files, but cannot silently shadow common ones.
        for name, data in profiles.items():
            overrides = data.get('overrides', [])
            for path in (Path(root) / 'profiles' / name / 'config').rglob('*'):
                if path.is_file():
                    relative = path.relative_to(Path(root) / 'profiles' / name / 'config')
                    if (Path(root) / 'common/config' / relative).exists() and relative.as_posix() not in overrides:
                        errors.append(f'Undeclared common override: {name}/{relative}')
        report(not errors, 'Core sources and platform registry: ' + ('; '.join(errors) if errors else 'one canonical source; supported/planned profiles explicit'))
        return profiles
    except (OSError, ValueError, KeyError) as exc:
        report(False, 'Platform registry: ' + str(exc))
        return {}
