"""System theme transactions run against a temporary filesystem, never /etc."""
import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import stat
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
from support import source_path, configure_imports, shell_bytes
configure_imports()

sys.path.insert(0, str(ROOT / 'scripts'))
import deploy
import sddm_theme as sddm


def fixture_directory(root, path):
    """Model system directories as 0755, independent of the caller's umask.

    Only newly created fixture directories are normalized. Existing paths keep
    their modes, so an unsafe directory injected by a security test stays unsafe.
    """
    path.relative_to(root)
    if '..' in path.parts:
        raise ValueError('Fixture directory cannot contain traversal')
    missing = []
    parent = path
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o755)
        directory.chmod(0o755)


class SystemThemeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-sddm-')
        self.root = Path(self.temp.name)
        self.theme = sddm.SystemTheme(self.root, actor_uid=1000)
        self.quiet = contextlib.ExitStack()
        self.quiet.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.quiet.enter_context(contextlib.redirect_stderr(io.StringIO()))
        for name in ('etc', 'usr', 'var'):
            fixture_directory(self.root, self.root / name)
        # SDDM is a prerequisite in production; its package-owned parent exists.
        fixture_directory(self.root, self.root / 'usr/share/sddm/themes')
        self.write(sddm.SESSION, '[Desktop Entry]\nName=Hyprland (uwsm-managed)\nExec=uwsm start -e -D Hyprland hyprland.desktop\n')

    def tearDown(self):
        self.quiet.close()
        self.temp.cleanup()

    def write(self, name, content):
        path = self.theme.path(name)
        fixture_directory(self.root, path.parent)
        path.write_text(content)
        path.chmod(0o644)
        return path

    def test_install_noop_restore_preserves_other_theme_and_personal_files(self):
        personal = self.write(sddm.THEME_DIR + '/personal.txt', 'mine')
        old_theme = self.write('/usr/share/sddm/themes/debian/Main.qml', '// Debian')
        session = self.theme.path(sddm.SESSION).read_bytes()
        identifier = self.theme.install()
        self.assertEqual(self.theme.check_installed(), [])
        self.assertIsNone(self.theme.install())
        self.assertEqual((self.theme.path(sddm.THEME_DIR) / 'min_forest.jpg').read_bytes(),
                         (source_path(ROOT, 'wallpapers/min_forest.jpg')).read_bytes())
        self.theme.restore(identifier)
        self.assertEqual(personal.read_text(), 'mine')
        self.assertEqual(old_theme.read_text(), '// Debian')
        self.assertFalse(self.theme.path(sddm.CONFIG).exists())
        self.assertFalse((self.theme.path(sddm.THEME_DIR) / 'Main.qml').exists())
        self.assertEqual(self.theme.path(sddm.SESSION).read_bytes(), session)
        self.theme.restore(identifier)  # resumable combined restoration

    def test_receiver_authorization_units_and_system_theme_share_restore_transaction(self):
        identifier = self.theme.install()
        authorization = self.theme.path(sddm.SYNC_USERS)
        self.assertEqual(json.loads(authorization.read_text()), {'format': 1, 'uids': [1000]})
        self.assertEqual(authorization.stat().st_mode & 0o777, 0o644)
        for name in sddm.SYNC_FILES:
            self.assertTrue(self.theme.path(name).is_file())
        self.assertIn(sddm.SYNC_PALETTE, self.theme.path(sddm.THEME_DIR + '/theme.conf').read_text())
        self.theme.restore(identifier)
        self.assertFalse(authorization.exists())
        self.assertTrue(all(not self.theme.path(name).exists() for name in sddm.SYNC_FILES))

    def test_additional_installer_enrolls_only_its_uid_and_restores_previous_policy(self):
        self.theme.install()
        other = sddm.SystemTheme(self.root, actor_uid=1001)
        identifier = other.install()
        self.assertEqual(json.loads(other.path(sddm.SYNC_USERS).read_text())['uids'], [1000, 1001])
        other.restore(identifier)
        self.assertEqual(json.loads(other.path(sddm.SYNC_USERS).read_text())['uids'], [1000])

    def test_dynamic_check_accepts_no_snapshot_and_detects_corrupt_copy(self):
        self.theme.install()
        self.assertEqual(self.theme.dynamic_errors(), [])
        from sddm_sync import Receiver, ROLES
        from engine import defaults
        image = source_path(ROOT, 'wallpapers/min_forest.jpg')
        import hashlib
        request = {'format': 1, 'palette': {k: defaults(ROOT / 'common/theme')[k] for k in ROLES},
                   'image_hash': hashlib.sha256(image.read_bytes()).hexdigest()}
        state = self.theme.path('/var/lib/hyprixe/theme')
        with image.open('rb') as stream:
            Receiver(state).receive(request, stream.fileno(), image.stat().st_uid)
        self.assertEqual(self.theme.dynamic_errors(), [])
        (state / 'current/palette.json').write_text('{broken')
        self.assertTrue(self.theme.dynamic_errors())

    def test_higher_priority_config_is_backed_up_without_changing_session_settings(self):
        original = '[Theme]\nCurrent=debian\nThemeDir=/opt/themes\nCursorTheme=breeze\n[Autologin]\nUser=alice\nSession=hyprland-uwsm.desktop\n[Wayland]\nSessionDir=/usr/share/wayland-sessions\n[General]\nDisplayServer=x11\n'
        top = self.write('/etc/sddm.conf', original)
        top.chmod(0o640)
        late = self.write('/etc/sddm.conf.d/zzz-personal.conf', '[Theme]\nCurrent=another\n[Users]\nRememberLastSession=true\n')
        late_before = late.read_bytes()
        identifier = self.theme.install()
        self.assertEqual(self.theme.effective_theme(), (sddm.THEME, '/usr/share/sddm/themes'))
        self.assertIn('Session=hyprland-uwsm.desktop', top.read_text())
        self.assertIn('DisplayServer=x11', top.read_text())
        self.assertIn('CursorTheme=breeze', top.read_text())
        self.assertIn('RememberLastSession=true', late.read_text())
        self.theme.restore(identifier)
        self.assertEqual(top.read_text(), original)
        self.assertEqual(top.stat().st_mode & 0o777, 0o640)
        self.assertEqual(late.read_bytes(), late_before)

    def test_virtual_keyboard_is_disabled_despite_higher_priority_overrides_and_restores(self):
        original = '[General]\nInputMethod=qtvirtualkeyboard\nDisplayServer=x11\n[Users]\nRememberLastSession=true\n'
        top = self.write('/etc/sddm.conf', original)
        late = self.write('/etc/sddm.conf.d/zzz-keyboard.conf', '[General]\nInputMethod=ibus\nNumlock=on\n')
        late_before = late.read_bytes()
        identifier = self.theme.install()
        self.assertEqual(self.theme.configuration().get('General', 'InputMethod'), '')
        self.assertIn('InputMethod=\n', self.theme.path(sddm.CONFIG).read_text())
        self.assertIn('DisplayServer=x11', top.read_text())
        self.assertIn('Numlock=on', late.read_text())
        self.assertEqual(self.theme.check_installed(), [])
        self.assertIsNone(self.theme.install())
        self.theme.restore(identifier)
        self.assertEqual(top.read_text(), original)
        self.assertEqual(late.read_bytes(), late_before)

    def test_reenabled_virtual_keyboard_is_reported(self):
        self.theme.install()
        self.write('/etc/sddm.conf', '[General]\nInputMethod=qtvirtualkeyboard\n')
        self.assertIn('InputMethod', '\n'.join(self.theme.check_installed()))

    def test_theme_does_not_force_a_keyboard_and_detector_rejects_a_panel(self):
        self.assertEqual(sddm.virtual_keyboard_sources(source_path(ROOT, 'sddm/themes') / sddm.THEME), [])
        qml = self.root / 'Injected.qml'
        for code in ('import QtQuick.VirtualKeyboard\nInputPanel {}',
                     'Item { Component.onCompleted: Qt.inputMethod.show() }'):
            qml.write_text(code)
            self.assertEqual(sddm.virtual_keyboard_sources(self.root), ['Injected.qml'])

    def test_changed_file_blocks_entire_restore(self):
        identifier = self.theme.install()
        main = self.theme.path(sddm.THEME_DIR + '/Main.qml')
        main.write_text('// personal edit')
        config_before = self.theme.path(sddm.CONFIG).read_bytes()
        with self.assertRaisesRegex(ValueError, 'Nothing restored'):
            self.theme.restore(identifier)
        self.assertEqual(self.theme.path(sddm.CONFIG).read_bytes(), config_before)

    def test_corrupt_backup_is_detected_before_restore(self):
        self.write('/etc/sddm.conf', '[Theme]\nCurrent=debian\n')
        identifier = self.theme.install()
        backup, manifest = self.theme.read(identifier)
        entry = next(e for e in manifest['files'] if e['before'])
        (backup / 'files' / entry['backup']).write_text('corrupt')
        with self.assertRaisesRegex(ValueError, 'corrupt'):
            self.theme.restore(identifier)
        self.assertEqual(self.theme.effective_theme()[0], sddm.THEME)

    def test_symlinked_system_target_and_backup_state_are_refused(self):
        outside = self.root / 'outside'
        outside.mkdir()
        themes = self.theme.path('/usr/share/sddm/themes')
        fixture_directory(self.root, themes)
        (themes / sddm.THEME).symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            self.theme.install()
        self.assertEqual(list(outside.iterdir()), [])
        (themes / sddm.THEME).unlink()
        state = self.theme.path('/var/lib/hyprixe')
        fixture_directory(self.root, state.parent)
        state.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            self.theme.install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_write_failure_rolls_back_system_changes(self):
        self.write('/etc/sddm.conf', '[Theme]\nCurrent=debian\n')
        original_atomic = sddm.atomic
        def fail_once(path, data, mode=0o600):
            if str(path).endswith('/theme.conf'):
                raise OSError('simulated disk failure')
            return original_atomic(path, data, mode)
        with patch.object(sddm, 'atomic', side_effect=fail_once):
            with self.assertRaisesRegex(OSError, 'disk failure'):
                self.theme.install()
        self.assertEqual(self.theme.path('/etc/sddm.conf').read_text(), '[Theme]\nCurrent=debian\n')
        self.assertFalse(self.theme.path(sddm.THEME_DIR + '/Main.qml').exists())

    def test_backup_ownership_is_checked(self):
        identifier = self.theme.install()
        with self.assertRaisesRegex(ValueError, 'another installing user'):
            sddm.SystemTheme(self.root, actor_uid=1001).restore(identifier)

    def test_dry_run_writes_nothing(self):
        before = sorted(str(p) for p in self.root.rglob('*'))
        self.theme.install(dry=True)
        self.assertEqual(sorted(str(p) for p in self.root.rglob('*')), before)

    def test_missing_files_and_overriding_selection_have_clear_diagnostics(self):
        self.theme.install()
        self.theme.path(sddm.THEME_DIR + '/Main.qml').unlink()
        self.write('/etc/sddm.conf', '[Theme]\nCurrent=other\n')
        self.theme.path(sddm.SESSION).unlink()
        failures = '\n'.join(self.theme.check_installed())
        self.assertIn('Main.qml', failures)
        self.assertIn('Effective SDDM', failures)
        self.assertIn('session entry', failures)

    def test_session_search_path_and_hidden_entry_are_diagnosed(self):
        self.theme.install()
        self.write('/etc/sddm.conf', '[Wayland]\nSessionDir=/opt/other-sessions\n')
        self.assertIn('SessionDir', '\n'.join(self.theme.check_installed()))
        self.write(sddm.SESSION, '[Desktop Entry]\nName=Hyprland (uwsm-managed)\nExec=uwsm start -e -D Hyprland hyprland.desktop\nHidden=true\n')
        self.assertIn('hidden', '\n'.join(self.theme.check_installed()))

    def test_installed_theme_permissions_are_checked(self):
        self.theme.install()
        self.theme.path(sddm.THEME_DIR + '/Main.qml').chmod(0o600)
        self.assertIn('not readable', '\n'.join(self.theme.check_installed()))
        # Installation repairs file permissions and restore puts the old mode back.
        identifier = self.theme.install()
        self.assertEqual(self.theme.check_installed(), [])
        self.theme.restore(identifier)
        self.assertEqual(self.theme.path(sddm.THEME_DIR + '/Main.qml').stat().st_mode & 0o777, 0o600)

    def test_missing_source_asset_aborts_without_system_writes(self):
        missing_repo = self.root / 'missing source repo'
        missing_repo.mkdir()
        with self.assertRaisesRegex(ValueError, 'Missing'):
            sddm.SystemTheme(self.root, repo=missing_repo).install()
        self.assertFalse(self.theme.path(sddm.CONFIG).exists())
        self.assertFalse(self.theme.path(sddm.BACKUPS).exists())

    @unittest.skipUnless(os.geteuid() == 0, 'root required for CLI lock/owner test in an isolated filesystem')
    def test_privileged_cli_install_list_noop_and_restore_in_isolated_filesystem(self):
        def command(*args):
            output = io.StringIO()
            with patch.object(sddm, 'SystemTheme', return_value=self.theme), \
                    patch.object(sddm, 'prerequisites'), \
                    patch.object(sys, 'argv', ['sddm_theme.py', *args]), \
                    contextlib.redirect_stdout(output):
                sddm.main()
            return output.getvalue()
        identifier = json.loads(command('install'))['backup']
        self.assertIn(identifier, command('restore', '--list'))
        self.assertIsNone(json.loads(command('install'))['backup'])
        command('restore', '--backup', identifier, '--dry-run')
        self.assertEqual(self.theme.check_installed(), [])
        command('restore', '--backup', identifier)
        self.assertFalse(self.theme.path(sddm.CONFIG).exists())


class SystemRootSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-root-boundary-')
        self.addCleanup(self.temp.cleanup)
        self.host = Path(self.temp.name)
        self.root = self.host / 'system image'
        self.root.mkdir(mode=0o700)
        self.theme = sddm.SystemTheme(self.root, actor_uid=1000)
        for name in ('etc', 'usr', 'var'):
            fixture_directory(self.root, self.root / name)

    @contextlib.contextmanager
    def metadata(self, target, *, uid=None, mode=None):
        # Inject stat metadata without needing chown/root on the physical PC.
        original = Path.stat
        def changed(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            if path == target:
                values = list(info)
                if uid is not None:
                    values[stat.ST_UID] = uid
                if mode is not None:
                    values[stat.ST_MODE] = stat.S_IFMT(info.st_mode) | mode
                return os.stat_result(values)
            return info
        with patch.object(Path, 'stat', changed):
            yield

    def authorization(self):
        path = self.theme.path(sddm.SYNC_USERS)
        fixture_directory(self.root, path.parent)
        path.write_text('{"format":1,"uids":[1000]}')
        path.chmod(0o644)
        return path

    def test_virtual_absolute_paths_map_inside_target_and_reject_traversal(self):
        self.assertEqual(self.theme.path('/etc/systemd/system'), self.root / 'etc/systemd/system')
        for path in ('../../etc/passwd', '/etc/../../etc/passwd', '//etc/passwd'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.theme.path(path)
        for path in (self.root / 'etc/../usr/libexec/hyprixe/sddm_sync.py',
                     self.host / 'outside/usr/libexec/hyprixe/sddm_sync.py',
                     Path('/etc/systemd/system/hyprixe-sddm-sync.service')):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'outside system root|traversal'):
                self.theme.guard(path)
        for path in (self.root / 'var/lib/hyprixe/sddm/../../../../etc/passwd',
                     Path('/var/lib/hyprixe/sddm/manifest.json')):
            with self.subTest(state=path), self.assertRaisesRegex(ValueError, 'outside system root|traversal'):
                self.theme.guard_state(path)

    def test_root_itself_must_be_canonical_and_not_a_symlink(self):
        alias = self.host / 'alias'; alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlinked system root'):
            sddm.SystemTheme(alias)
        for path in (Path('relative-root'), self.root / '..' / self.root.name):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'absolute canonical'):
                sddm.SystemTheme(path)

    def test_host_ancestors_are_not_part_of_the_simulated_system(self):
        self.host.chmod(0o777)
        self.theme.guard(self.theme.path(sddm.SYNC_USERS))
        self.theme.guard_state(self.theme.path(sddm.BACKUPS) / 'example')
        # This host directory is private again; only virtual-system parents
        # contribute to the greeter's traversal/permission checks.
        self.host.chmod(0o700)
        fixture_directory(self.root, self.root / 'usr/share/sddm/themes')
        session = self.theme.path(sddm.SESSION)
        fixture_directory(self.root, session.parent)
        session.write_text('[Desktop Entry]\nName=Hyprland (uwsm-managed)\nExec=uwsm start -e -D Hyprland hyprland.desktop\n')
        session.chmod(0o644)
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.theme.install()
        self.assertEqual(self.theme.check_installed(), [])

    def test_symlinked_usr_etc_and_var_never_reach_outside_fixture(self):
        for name in ('usr', 'etc', 'var'):
            with self.subTest(parent=name):
                target = self.host / ('outside-' + name)
                target.mkdir(mode=0o755)
                parent = self.root / name
                parent.rmdir(); parent.symlink_to(target, target_is_directory=True)
                try:
                    with self.assertRaisesRegex(ValueError, 'Symlinked'):
                        self.theme.install()
                    self.assertEqual(list(target.iterdir()), [])
                finally:
                    parent.unlink(); parent.mkdir(mode=0o755); parent.chmod(0o755)

    def test_target_file_symlink_is_rejected_without_changing_destination(self):
        target = self.host / 'personal-file'; target.write_text('unchanged')
        path = self.theme.path(sddm.SYNC_FILES[0])
        fixture_directory(self.root, path.parent)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'regular file'):
            self.theme.guard(path)
        self.assertEqual(target.read_text(), 'unchanged')

    def test_backup_directory_symlink_is_rejected(self):
        state = self.theme.path('/var/lib/hyprixe/sddm')
        self.theme.mkdir_state(state)
        outside = self.host / 'outside-backups'; outside.mkdir()
        (state / 'backups').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            self.theme.guard_state(state / 'backups/example/manifest.json')
        self.assertEqual(list(outside.iterdir()), [])

    def test_fixture_system_parents_keep_strict_modes(self):
        for name in ('usr', 'etc', 'var'):
            parent = self.root / name
            target = self.theme.path(sddm.SYNC_FILES[0] if name == 'usr' else sddm.SYNC_USERS)
            for mode in (0o775, 0o777):
                with self.subTest(parent=name, mode=oct(mode)):
                    parent.chmod(mode)
                    try:
                        with self.assertRaisesRegex(ValueError, 'Unsafe'):
                            if name == 'var':
                                self.theme.guard_state(self.theme.path(sddm.BACKUPS) / 'example')
                            else:
                                self.theme.guard(target)
                    finally:
                        parent.chmod(0o755)

    def test_fixture_system_parents_reject_unexpected_owners(self):
        for name in ('usr', 'etc', 'var'):
            with self.subTest(parent=name), self.metadata(self.root / name, uid=os.getuid() + 1):
                with self.assertRaisesRegex(ValueError, 'Unsafe'):
                    if name == 'var':
                        self.theme.guard_state(self.theme.path(sddm.BACKUPS) / 'example')
                    else:
                        self.theme.guard(self.theme.path(sddm.SYNC_FILES[0] if name == 'usr' else sddm.SYNC_USERS))

    def test_authorization_world_writable_is_rejected_before_deployment(self):
        path = self.authorization(); path.chmod(0o666)
        with self.assertRaisesRegex(ValueError, 'Unsafe SDDM sync authorization'):
            self.theme.payload()
        self.assertFalse(self.theme.path(sddm.BACKUPS).exists())

    def test_authorization_wrong_owner_is_rejected_without_root(self):
        path = self.authorization()
        with self.metadata(path, uid=os.getuid() + 1), self.assertRaisesRegex(ValueError, 'Unsafe SDDM sync authorization'):
            self.theme.payload()

    def test_backup_state_requires_safe_directory_owner_and_permissions(self):
        backup = self.theme.path(sddm.BACKUPS) / 'example'
        self.theme.mkdir_state(backup)
        backup.chmod(0o777)
        with self.assertRaisesRegex(ValueError, 'Unsafe SDDM backup/state'):
            self.theme.guard_state(backup / 'manifest.json')
        backup.chmod(0o700)
        with self.metadata(backup, uid=os.getuid() + 1), self.assertRaisesRegex(ValueError, 'Unsafe SDDM backup/state'):
            self.theme.guard_state(backup / 'manifest.json')

    def test_production_root_keeps_uid_zero_and_strict_etc_parent(self):
        with patch('sddm_theme.os.getuid', return_value=12345):
            production = sddm.SystemTheme()
        self.assertEqual(production.root, Path('/'))
        self.assertEqual(production.filesystem.owner_uid, 0)
        for changes in ({'uid': 12345}, {'mode': 0o777}):
            with self.subTest(changes=changes), self.metadata(Path('/etc'), **changes):
                with self.assertRaisesRegex(ValueError, 'Unsafe synchronization integration parent'):
                    production.guard(production.path(sddm.SYNC_USERS))


class FixtureEnvironmentTests(unittest.TestCase):
    def test_transactions_work_with_group_writable_and_restrictive_umasks(self):
        code = ('import os,sys,unittest; os.umask(int(sys.argv[1],8)); '
                'suite=unittest.defaultTestLoader.loadTestsFromName("test_sddm.SystemThemeTests"); '
                'result=unittest.TextTestRunner(verbosity=1).run(suite); '
                'sys.exit(not result.wasSuccessful())')
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                   PYTHONPATH=str(ROOT / 'tests') + os.pathsep + os.environ.get('PYTHONPATH', ''))
        for mode in ('002', '022', '077'):
            with self.subTest(umask=mode):
                result = subprocess.run([sys.executable, '-c', code, mode], env=env, cwd=ROOT,
                                        capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CombinedRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-combined-')
        self.home = Path(self.temp.name)
        self.roots = {name: self.home / name for name in ('config', 'data', 'state')}
        self.env = patch.dict(os.environ, HOME=str(self.home))
        self.env.start()
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.env.stop()
        self.temp.cleanup()

    def test_linked_system_backup_is_preflighted_and_restored(self):
        with patch.object(deploy, 'system_theme', side_effect=['', '{"backup":"system-id"}']) as root:
            backup = deploy.install_with_sddm(self.home, self.roots, 'native')
        self.assertEqual(deploy.read_manifest(backup)['sddm_backup'], 'system-id')
        with patch.object(deploy, 'system_theme', return_value='') as root:
            deploy.restore(backup, self.home)
        self.assertEqual(root.call_args_list[0].args, ('restore', '--backup', 'system-id', '--dry-run'))
        self.assertEqual(root.call_args_list[1].args, ('restore', '--backup', 'system-id'))
        self.assertFalse((self.roots['config'] / 'hypr/hyprland.lua').exists())

    def test_system_failure_rolls_back_user_deployment(self):
        with patch.object(deploy, 'system_theme', side_effect=['', subprocess.CalledProcessError(1, 'system install')]):
            with self.assertRaises(subprocess.CalledProcessError):
                deploy.install_with_sddm(self.home, self.roots, 'native')
        self.assertFalse((self.roots['config'] / 'hypr/hyprland.lua').exists())

    def test_system_only_change_creates_restorable_user_transaction(self):
        deploy.install(self.home, self.roots, 'native')
        with patch.object(deploy, 'system_theme', side_effect=['', '{"backup":"system-id"}']):
            backup = deploy.install_with_sddm(self.home, self.roots, 'native')
        self.assertEqual(deploy.read_manifest(backup)['files'], [])
        self.assertEqual(deploy.read_manifest(backup)['sddm_backup'], 'system-id')

    def test_system_restore_conflict_leaves_user_files_untouched(self):
        with patch.object(deploy, 'system_theme', side_effect=['', '{"backup":"system-id"}']):
            backup = deploy.install_with_sddm(self.home, self.roots, 'native')
        target = self.roots['config'] / 'hypr/hyprland.lua'
        before = target.read_bytes()
        with patch.object(deploy, 'system_theme', side_effect=subprocess.CalledProcessError(1, 'restore conflict')) as root:
            with self.assertRaises(subprocess.CalledProcessError):
                deploy.restore(backup, self.home)
        self.assertEqual(root.call_count, 1)
        self.assertEqual(target.read_bytes(), before)

    def test_user_restore_conflict_does_not_call_system_restore(self):
        with patch.object(deploy, 'system_theme', side_effect=['', '{"backup":"system-id"}']):
            backup = deploy.install_with_sddm(self.home, self.roots, 'native')
        (self.roots['config'] / 'hypr/hyprland.lua').write_text('-- personal')
        with patch.object(deploy, 'system_theme') as root:
            with self.assertRaisesRegex(ValueError, 'Nothing restored'):
                deploy.restore(backup, self.home)
            root.assert_not_called()


class QmlRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('PyQt6') and importlib.util.find_spec('PyQt6.QtQuick'),
                         'optional python3-pyqt6.qtquick needed for QML interaction tests')
    def test_qt6_models_login_errors_power_and_responsive_layout(self):
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
        result = subprocess.run([sys.executable, str(ROOT / 'tests/sddm_qml_smoke.py')],
                                env=env, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
