import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('deploy', ROOT / 'scripts/deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-test-')
        self.home = Path(self.temp.name) / 'home with spaces'
        self.home.mkdir()
        self.env = patch.dict(os.environ, {'HOME': str(self.home), 'XDG_CONFIG_HOME': str(self.home / '.config'),
                                          'XDG_DATA_HOME': str(self.home / '.local/share'),
                                          'XDG_STATE_HOME': str(self.home / '.local/state')})
        self.env.start()
        _, self.roots = deploy.locations()
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.env.stop()
        self.temp.cleanup()

    def backups(self):
        return sorted((self.roots['state'] / 'hyprixe/backups').glob('*'))

    def install(self, profile='native', **kw):
        deploy.install(self.home, self.roots, profile, **kw)

    def write(self, name, text):
        path = self.roots['config'] / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_native_install_and_noop_repeat(self):
        self.install()
        before = self.backups()
        self.assertEqual(len(before), 1)
        self.install()
        self.assertEqual(self.backups(), before)
        self.assertNotIn('LIBGL', (self.roots['config'] / 'hypr/profile.lua').read_text())
        self.assertTrue((self.roots['config'] / 'hypr/scripts/Wallpaper.sh').stat().st_mode & 0o111)
        self.assertEqual((self.roots['data'] / 'hyprixe/wallpapers/min_forest.jpg').read_bytes(), (ROOT / 'wallpapers/min_forest.jpg').read_bytes())

    def test_persistent_workspaces_deploy_for_waybar_and_compositor(self):
        import shutil
        import subprocess
        self.install()
        hypr = self.roots['config'] / 'hypr'
        bar = json.loads((hypr / 'waybar/configs/Frosted-Glass').read_text())
        self.assertEqual(bar['hyprland/workspaces']['persistent-workspaces'], {'*': [1, 2, 3, 4]})
        self.assertEqual(bar['hyprland/workspaces']['sort-by'], 'number')
        self.assertEqual(bar['modules-left'][0], 'hyprland/workspaces')
        self.assertTrue((hypr / 'lua/workspaces.lua').is_file())
        self.assertIn('lua/workspaces.lua', (hypr / 'hyprland.lua').read_text())
        if shutil.which('lua'):
            result = subprocess.run(['lua', str(ROOT / 'tests/check_lua.lua'), str(self.roots['config'])],
                                    env=dict(os.environ, XDG_CONFIG_HOME=str(self.roots['config'])),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_existing_config_backup_restore_and_personal_file(self):
        old = self.write('hypr/hyprland.lua', 'old config\n')
        personal = self.write('hypr/personal.txt', 'keep me')
        legacy = self.write('hypr/hyprland.conf', 'legacy')
        old.chmod(0o600)
        self.install()
        self.assertFalse(legacy.exists())
        backup = self.backups()[0]
        deploy.restore(backup, self.home)
        self.assertEqual(old.read_text(), 'old config\n')
        self.assertEqual(old.stat().st_mode & 0o777, 0o600)
        self.assertEqual(personal.read_text(), 'keep me')
        self.assertEqual(legacy.read_text(), 'legacy')
        self.assertFalse((self.roots['data'] / 'hyprixe/wallpapers/min_forest.jpg').exists())

    def test_vmware_then_native_then_restore_profile(self):
        self.install('vmware')
        self.assertIn('llvmpipe', (self.roots['config'] / 'hypr/profile.lua').read_text())
        self.install('native')
        self.assertNotIn('llvmpipe', (self.roots['config'] / 'hypr/profile.lua').read_text())
        deploy.restore(self.backups()[-1], self.home)
        self.assertIn('llvmpipe', (self.roots['config'] / 'hypr/profile.lua').read_text())
        deploy.restore(self.backups()[0], self.home)
        self.assertFalse((self.roots['config'] / 'hypr/hyprland.lua').exists())

    def test_changed_file_blocks_restore_without_partial_changes(self):
        self.install()
        target = self.write('hypr/hyprland.lua', 'personal edit')
        other = self.roots['config'] / 'alacritty/alacritty.toml'
        before = other.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Nothing restored'):
            deploy.restore(self.backups()[0], self.home)
        self.assertEqual(other.read_bytes(), before)
        self.assertEqual(target.read_text(), 'personal edit')

    def test_dry_run_creates_no_configs_or_backups(self):
        self.install(dry=True)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_symlinked_parent_is_refused(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.home / '.config').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_file_symlink_is_backed_up_and_restored(self):
        real = self.home / 'original'
        real.write_text('external config')
        link = self.write('hypr/hyprland.lua', '')
        link.unlink()
        link.symlink_to(real)
        self.install()
        self.assertFalse(link.is_symlink())
        deploy.restore(self.backups()[0], self.home)
        self.assertTrue(link.is_symlink())
        self.assertEqual(real.read_text(), 'external config')

    def test_merge_preserves_unrelated_mime_kde_and_qt_settings(self):
        self.write('mimeapps.list', '# personal\n[Default Applications]\ntext/plain=editor.desktop;\n')
        self.write('kdeglobals', '[Unrelated]\nKeep=yes\n')
        self.write('qt6ct/qt6ct.conf', '[Fonts]\nKeep=font\n')
        self.install()
        self.assertIn('text/plain=editor.desktop;', (self.roots['config'] / 'mimeapps.list').read_text())
        self.assertIn('inode/directory=org.kde.dolphin.desktop;', (self.roots['config'] / 'mimeapps.list').read_text())
        self.assertIn('Keep=yes', (self.roots['config'] / 'kdeglobals').read_text())
        self.assertIn('Keep=font', (self.roots['config'] / 'qt6ct/qt6ct.conf').read_text())

    def test_io_error_rolls_back_successful_writes(self):
        old = self.write('hypr/hyprland.lua', 'old config')
        real_atomic = deploy.atomic
        failed = False
        def failing(path, data, mode=0o600):
            nonlocal failed
            if path.name == 'kdeglobals' and not failed:
                failed = True
                raise OSError('simulated disk failure')
            real_atomic(path, data, mode)
        with patch.object(deploy, 'atomic', failing):
            with self.assertRaisesRegex(OSError, 'disk failure'):
                self.install()
        self.assertEqual(old.read_text(), 'old config')
        self.assertTrue((self.backups()[0] / 'rolled-back').exists())

    def test_custom_xdg_paths_are_rendered(self):
        self.roots['config'] = self.home / 'settings'
        self.roots['data'] = self.home / 'data'
        self.install()
        lock = (self.roots['config'] / 'hypr/hyprlock.conf').read_text()
        self.assertIn(str(self.home / 'data/hyprixe/wallpapers/min_forest.jpg'), lock)
        waybar = self.roots['config'] / 'hypr/waybar/configs/Frosted-Glass'
        self.assertEqual(json.loads(waybar.read_text()),
                         json.loads((ROOT / '.config/hypr/waybar/configs/Frosted-Glass').read_text()))
        self.assertFalse((self.roots['config'] / 'hypr/waybar/config').exists())
        style = self.roots['config'] / 'hypr/waybar/style.css'
        self.assertTrue(style.is_file())
        self.assertTrue((style.parent / 'style/Frosted-Glass.css').is_file())
        unit = (self.roots['config'] / 'systemd/user/waybar.service.d/hyprixe.conf').read_text()
        self.assertIn(f'-c "{waybar}" -s "{style}"', unit)
        self.assertNotIn('@HYPR_CONFIG@', unit)
        for name, script in (('hyprixe-awww', 'WallpaperDaemon.sh'),
                             ('hyprixe-wallpaper', 'Wallpaper.sh'),
                             ('hyprixe-polkit', 'Polkit.sh'),
                             ('hyprixe-clipboard', 'ClipboardWatcher.sh')):
            service = (self.roots['config'] / f'systemd/user/{name}.service').read_text()
            self.assertIn(f'ExecStart="{self.roots["config"]}/hypr/scripts/{script}"', service)
            self.assertNotIn('@HYPR_CONFIG@', service)
        idle = (self.roots['config'] / 'systemd/user/hypridle.service.d/hyprixe.conf').read_text()
        self.assertIn(f'-c "{self.roots["config"]}/hypr/hypridle.conf"', idle)
        self.assertIn('EnvironmentFile=-%t/uwsm/env_session.conf', idle)

    def test_missing_active_waybar_files_abort_before_writing(self):
        source = Path(self.temp.name) / 'incomplete-repository'
        for missing in ('configs/Frosted-Glass', 'style.css', 'style/Frosted-Glass.css'):
            with self.subTest(missing=missing):
                for relative in ('configs/Frosted-Glass', 'style.css', 'style/Frosted-Glass.css'):
                    path = source / '.config/hypr/waybar' / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if relative == missing:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_text('fixture')
                with patch.object(deploy, 'REPO', source):
                    with self.assertRaisesRegex(FileNotFoundError, 'Required Waybar file missing'):
                        self.install()
                self.assertEqual(list(self.home.iterdir()), [])

    def test_backup_corruption_is_detected_before_restore(self):
        self.write('hypr/hyprland.lua', 'original')
        self.install()
        backup = self.backups()[0]
        manifest = deploy.read_manifest(backup)
        entry = next(e for e in manifest['files'] if e['backup'] is not None)
        (backup / 'files' / entry['backup']).write_text('corruption')
        with self.assertRaisesRegex(ValueError, 'corrupt'):
            deploy.restore(backup, self.home)
        self.assertTrue((self.roots['config'] / 'hypr/hyprland.lua').is_file())

    def test_invalid_profile_rejected_by_cli(self):
        import subprocess
        r = subprocess.run(['python3', str(ROOT / 'scripts/deploy.py'), 'install', '--profile', 'invalid'], capture_output=True)
        self.assertEqual(r.returncode, 2)

    def test_xdg_outside_home_is_refused(self):
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': '/etc'}):
            with self.assertRaisesRegex(ValueError, 'subdirectory'):
                deploy.locations()

    def test_runtime_binaries_are_backed_up_and_restored(self):
        stage = Path(self.temp.name) / 'stage'
        stage.mkdir()
        (stage / 'awww').write_bytes(b'new executable')
        (stage / 'waybar').write_bytes(b'compatible Waybar executable')
        binpath = self.home / '.local/bin/awww'
        binpath.parent.mkdir(parents=True)
        binpath.write_bytes(b'old executable')
        self.install(runtime=stage)
        self.assertEqual(binpath.read_bytes(), b'new executable')
        unit = (self.roots['config'] / 'systemd/user/waybar.service.d/hyprixe.conf').read_text()
        self.assertIn(str(self.home / '.local/bin/waybar'), unit)
        self.assertNotIn('@WAYBAR_EXEC@', unit)
        deploy.restore(self.backups()[0], self.home)
        self.assertEqual(binpath.read_bytes(), b'old executable')
        self.assertFalse((self.home / '.local/bin/waybar').exists())

    def test_permission_only_change_restores_original_mode(self):
        source = ROOT / '.config/hypr/scripts/Wallpaper.sh'
        target = self.write('hypr/scripts/Wallpaper.sh', source.read_text())
        target.chmod(0o600)
        self.install()
        self.assertEqual(target.stat().st_mode & 0o777, 0o755)
        deploy.restore(self.backups()[0], self.home)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
