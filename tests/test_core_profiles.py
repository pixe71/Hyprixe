"""Architecture invariants and frozen pre-refactor Debian deployment contract."""
import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from support import ROOT, source_path, configure_imports, shell_bytes
from source_layout import detect_profile, mapped_files, profile_metadata
from profile_checks import check_sources, duplication_errors, registry
from run_tests import select
import deploy
import sddm_theme

FIXTURES = ROOT / 'tests/fixtures'


class CoreProfileTests(unittest.TestCase):
    def test_supported_debian_planned_nixos_and_no_duplicated_sources(self):
        results = []
        profiles = check_sources(lambda ok, message: results.append((ok, message)), ROOT)
        self.assertTrue(all(ok for ok, _ in results), results)
        self.assertEqual(profiles['debian']['status'], 'supported')
        self.assertEqual(profiles['nixos']['status'], 'planned')
        self.assertEqual(sorted(p.name for p in (ROOT / 'profiles/nixos').iterdir()), ['README.md', 'profile.json'])
        for old in ('.config', '.local', 'wallpapers', 'sddm', '.zshrc', '.p10k.zsh', 'profiles/vmware'):
            self.assertFalse((ROOT / old).exists(), old)
        # Git does not track empty directories left by a local move.
        self.assertFalse(any(p.is_file() for p in (ROOT / 'profiles/native').rglob('*')))

    def test_accidental_copies_are_detected_even_under_another_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / 'common/config/hypr/rofi/config.rasi'
            original.parent.mkdir(parents=True)
            original.write_text('canonical rofi fixture')
            for name in ('debian', 'nixos'):
                duplicate = root / 'profiles' / name / 'rofi/copied.json'
                duplicate.parent.mkdir(parents=True)
                shutil.copyfile(original, duplicate)
            self.assertEqual(len(duplication_errors(root)), 2)

    def test_unknown_metadata_and_undeclared_overrides_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'profiles', root / 'profiles')
            (root / 'tests').mkdir()
            for module in profile_metadata('debian')['tests']:
                (root / 'tests' / (module + '.py')).write_text('# metadata fixture\n')
            path = root / 'profiles/nixos/profile.json'
            data = json.loads(path.read_text())
            data['status'] = 'supported'
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'backend and regression tests'):
                registry(root)
            data['status'] = 'planned'
            path.write_text(json.dumps(data))
            # Debian's backend exists in this fixture. A divergent shadow still
            # requires a declared override, even though its hash differs.
            path = root / 'common/config/hypr/scripts/Polkit.sh'
            path.parent.mkdir(parents=True)
            path.write_text('different core content')
            results = []
            check_sources(lambda ok, message: results.append((ok, message)), root)
            self.assertFalse(results[0][0], results)
            self.assertIn('Undeclared common override', results[0][1])
            module = profile_metadata('debian')['tests'][0]
            (root / 'tests' / (module + '.py')).unlink()
            with self.assertRaisesRegex(ValueError, 'test module missing'):
                registry(root)

    def test_detection_does_not_confuse_hardware_and_platform_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'os-release'
            for text, expected in (('ID=debian\nVERSION_ID="13"\n', 'debian'),
                                   ('ID=nixos\n', 'nixos'), ('ID=debian\nVERSION_ID="12"\n', None)):
                path.write_text(text)
                self.assertEqual(detect_profile(path), expected)
        with self.assertRaises(ValueError):
            profile_metadata('native')

    def test_test_groups_are_disjoint_complete_and_planned_not_supported(self):
        import unittest as loader
        from run_tests import flatten
        tests = list(flatten(loader.defaultTestLoader.discover(str(ROOT / 'tests'))))
        profiles = registry(ROOT)
        common = {t.id() for t in select(tests, profiles, 'common')}
        debian = {t.id() for t in select(tests, profiles, 'debian')}
        self.assertFalse(common & debian)
        self.assertEqual(common | debian, {t.id() for t in tests})
        self.assertFalse(list(select(tests, profiles, 'nixos')))
        # A failure in any required group is propagated by the runner/verifier.
        self.assertIn('test_deploy.DeploymentTests.test_native_install_and_noop_repeat', debian)


class DebianEquivalenceTests(unittest.TestCase):
    PLATFORM = 'debian'

    def roots(self, home, custom=False):
        return {key: home / value for key, value in zip(('config', 'data', 'state'),
                ('settings with spaces', 'data with spaces', 'state with spaces') if custom else
                ('.config', '.local/share', '.local/state'))}

    def test_all_sixteen_frozen_payloads_have_identical_targets_hashes_and_modes(self):
        fixture = json.loads((FIXTURES / 'debian-v1-payload.json').read_text())
        self.assertEqual(len(fixture['cases']), 16)
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home with spaces'
            home.mkdir()
            stage = Path(tmp) / 'runtime'
            stage.mkdir()
            for name in ('rofi', 'waybar', 'awww', 'awww-daemon'):
                (stage / name).write_bytes(b'#!/bin/sh\nexit 0\n')
            for name, expected in fixture['cases'].items():
                xdg, hardware, scope = name.split('/')
                with self.subTest(case=name), patch.dict(os.environ, HOME=str(home)), patch.object(deploy.shutil, 'which', side_effect=lambda name: '/usr/bin/' + name):
                    payload = deploy.payload(self.roots(home, xdg == 'custom'), hardware,
                            runtime=stage if scope == 'runtime' else None,
                            waybar_only=scope == 'waybar', dolphin_only=scope == 'dolphin')
                    actual = {}
                    for target, (data, mode) in payload.items():
                        if data is not None:
                            try:
                                data = data.decode().replace(str(home), '@HOME@').encode()
                            except UnicodeDecodeError:
                                pass
                        actual[target.relative_to(home).as_posix()] = {
                            'sha256': hashlib.sha256(data).hexdigest() if data is not None else None, 'mode': mode}
                    self.assertEqual(actual, expected)
        self.assertEqual({name: hashlib.sha256(data).hexdigest() for name, data in sddm_theme.source_payload().items()}, fixture['sddm'])

    def test_mapping_covers_all_shared_sources_without_changed_destinations(self):
        entries = list(mapped_files())
        sources = {source for source, _, _ in entries}
        for prefix in ('common/config', 'common/local', 'common/shell', 'common/wallpapers'):
            self.assertEqual({p for p in (ROOT / prefix).rglob('*') if p.is_file()} - sources, set())
        destinations = [(namespace, relative) for _, namespace, relative in entries]
        self.assertEqual(len(destinations), len(set(destinations)))
        for logical, installed in (('.config/kitty/kitty.conf', ('config', Path('kitty/kitty.conf'))),
                                   ('.config/hypr/rofi/config.rasi', ('config', Path('hypr/rofi/config.rasi'))),
                                   ('.config/hypr/waybar/style.css', ('config', Path('hypr/waybar/style.css')))):
            self.assertIn((source_path(ROOT, logical), *installed), entries)

    def test_pre_refactor_format_one_backup_restores_original_files_and_modes(self):
        fixture = json.loads((FIXTURES / 'debian-v1-backup.json').read_text())
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            home = Path(tmp) / 'home'
            home.mkdir()
            manifest = json.loads(json.dumps(fixture['manifest']).replace('@HOME@', str(home)))
            self.assertEqual(manifest['format'], 1)
            originals = {}
            for entry in manifest['files']:
                if entry['backup'] is not None:
                    path = Path(entry['target'])
                    data = base64.b64decode(fixture['files'][entry['backup']])
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    path.chmod(entry['mode'])
                    originals[path] = (data, entry['mode'])
            with patch.dict(os.environ, HOME=str(home)):
                content = deploy.payload(self.roots(home), 'native')
            # Rebase only the transient HOME-dependent installed hashes. The
            # independent golden test above prevents content drift being hidden.
            for entry in manifest['files']:
                path = Path(entry['target'])
                data, mode = content[path]
                if data is not None:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    path.chmod(mode)
                entry['after'] = deploy.digest(path)
            backup = home / '.local/state/hyprixe/backups' / manifest['id']
            (backup / 'files').mkdir(parents=True)
            for name, data in fixture['files'].items():
                (backup / 'files' / name).write_bytes(base64.b64decode(data))
            (backup / 'manifest.json').write_text(json.dumps(manifest))
            personal = home / '.config/personal-notes'
            personal.write_text('preserve')
            before = {path: (path.read_bytes(), path.stat().st_mode & 0o777)
                      for path in content if path.is_file()}
            with patch.dict(os.environ, HOME=str(home)):
                self.assertIsNone(deploy.install(home, self.roots(home), 'native'))
                self.assertIsNone(deploy.install(home, self.roots(home), 'native'))
            self.assertEqual({path: (path.read_bytes(), path.stat().st_mode & 0o777)
                              for path in before}, before)
            self.assertEqual([p.name for p in backup.parent.iterdir()], [manifest['id']])
            deploy.restore(backup, home)
            for path, (data, mode) in originals.items():
                self.assertEqual(path.read_bytes(), data)
                self.assertEqual(path.stat().st_mode & 0o777, mode)
            self.assertFalse((home / '.config/wlogout/layout').exists())
            self.assertEqual(personal.read_text(), 'preserve')

    def test_moved_privileged_helper_starts_with_a_clean_python_environment(self):
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
        result = subprocess.run(['python3', '-I', str(source_path(ROOT, 'scripts/sddm_theme.py')), '--help'],
                                env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
