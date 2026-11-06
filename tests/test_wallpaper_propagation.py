"""One persistent selection, derived user link and explicit presentation semantics."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

import test_dynamic_theme as dynamic
from support import configure_imports
configure_imports()
import deploy
fixture, SWATCHES, engine, ROOT = dynamic.fixture, dynamic.SWATCHES, dynamic.engine, dynamic.ROOT


class WallpaperPropagationTests(unittest.TestCase):
    setUp = dynamic.TransactionTests.setUp
    generate = dynamic.TransactionTests.generate

    def test_two_images_update_one_link_and_configs_never_change(self):
        roots = {'config': self.root / 'custom config', 'cache': self.root / 'cache',
                 'data': self.root / 'data', 'state': self.root / 'state'}
        payload = deploy.payload(roots, 'native', home=self.root)
        paths = ('hypr/rofi/themes/Frosted-Glass-Launcher.rasi', 'hypr/hyprlock.conf')
        configs = {name: payload[roots['config'] / name][0] for name in paths}
        for content in configs.values():
            self.assertIn(str(self.engine.current_wallpaper).encode(), content)
            self.assertNotIn(b'wallpapers/min_forest.jpg', content)
        second = fixture(self.root / 'purple B.png', SWATCHES['purple'])
        for image in (self.image, second):
            self.engine.transact(image, enabled=True, restore=True)
            self.assertEqual(self.engine.current_wallpaper.resolve(strict=True), image)
            self.assertEqual(self.engine.load_state()['wallpaper'], str(image))
            self.apply.assert_called_with(image)
            for name, original in configs.items():
                self.assertEqual(deploy.payload(roots, 'native', home=self.root)[roots['config'] / name][0], original)

    def test_restore_selected_wallpaper_reuses_palette_and_repairs_missing_link(self):
        self.generate()
        self.engine.current_wallpaper.unlink()
        meta = self.engine.read()
        self.extract.reset_mock(); self.apply.reset_mock(); self.reload.reset_mock()
        self.engine.transact(restore=True)
        self.assertEqual(self.engine.read(), meta)
        self.apply.assert_called_once_with(self.image)
        self.extract.assert_not_called(); self.reload.assert_not_called()
        self.assertEqual(self.engine.current_wallpaper.resolve(), self.image)

    def test_restore_absent_state_uses_default_and_stays_disabled(self):
        self.engine.transact(restore=True)
        self.apply.assert_called_once_with(self.reference)
        self.assertEqual(self.engine.current_wallpaper.resolve(), self.reference)
        self.assertFalse(self.engine.load_state()['enabled'])

    def test_restore_corrupt_state_uses_default_without_overwriting_preferences(self):
        self.generate()
        self.engine.state_file.write_text('{broken')
        self.engine.transact(restore=True)
        self.assertEqual(self.engine.state_file.read_text(), '{broken')
        self.assertEqual(self.engine.current_wallpaper.resolve(), self.reference)
        self.assertFalse(self.engine.read()['enabled'])

    def test_missing_selected_image_repairs_broken_link_and_keeps_selection(self):
        self.generate(enabled=False)
        saved = self.engine.load_state()
        self.image.unlink()
        self.engine.transact(restore=True)
        self.assertEqual(self.engine.current_wallpaper.resolve(strict=True), self.reference)
        self.assertEqual(self.engine.load_state(), saved)

    def test_enable_disable_keep_image_default_resets_image_and_preserves_preference(self):
        self.generate(enabled=True)
        with patch('engine.Engine', return_value=self.engine):
            for action, enabled, image in [('disable', False, self.image), ('enable', True, self.image),
                                           ('default', True, self.reference), ('disable', False, self.reference)]:
                self.assertEqual(engine.main([action]), 0)
                self.assertEqual(self.engine.current_wallpaper.resolve(), image)
                self.assertEqual(self.engine.load_state()['enabled'], enabled)
                if action in ('default', 'disable'):
                    self.assertEqual(json.loads((self.engine.current / 'palette.json').read_text()), self.engine.base)

    def test_repeat_explicit_apply_reasserts_awww_without_reextracting(self):
        self.generate()
        self.apply.reset_mock(); self.extract.reset_mock()
        with patch('engine.Engine', return_value=self.engine):
            self.assertEqual(engine.main(['apply', str(self.image)]), 0)
        self.apply.assert_called_once_with(self.image)
        self.extract.assert_not_called()

    def test_default_then_login_does_not_recalculate_unchanged_palette(self):
        self.generate(enabled=True)
        self.engine.transact(use_default=True, force=True)
        self.extract.reset_mock()
        old = self.engine.read()
        self.engine.transact(restore=True)
        self.extract.assert_not_called()
        self.assertEqual(self.engine.read(), old)

    def test_failed_activation_rolls_back_stable_link_and_selection(self):
        self.generate()
        second = fixture(self.root / 'second.png', SWATCHES['purple'])
        self.reload.side_effect = [ValueError('reload failed'), []]
        saved = self.engine.load_state()
        with self.assertRaises(ValueError):
            self.engine.transact(second)
        self.assertEqual(self.engine.current_wallpaper.resolve(), self.image)
        self.assertEqual(self.engine.load_state(), saved)

    def test_unmanaged_stable_regular_file_is_preserved(self):
        self.engine.current_wallpaper.write_text('user data')
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            self.generate()
        self.assertEqual(self.engine.current_wallpaper.read_text(), 'user data')
        self.apply.assert_not_called()

    def test_rollback_repairs_previously_missing_presentation_link(self):
        self.generate()
        self.engine.current_wallpaper.unlink()
        second = fixture(self.root / 'another.png', SWATCHES['purple'])
        self.reload.side_effect = [ValueError('reload failed'), []]
        with self.assertRaises(ValueError):
            self.engine.transact(second)
        self.assertEqual(self.engine.current_wallpaper.resolve(strict=True), self.image)

    def test_profile_hook_gets_real_image_and_current_palette_only_after_success(self):
        with patch.object(self.engine, 'sync_login_theme') as sync:
            self.generate()
            sync.assert_called_once_with(self.image)
            self.reload.side_effect = [ValueError('failed'), []]
            sync.reset_mock()
            with self.assertRaises(ValueError):
                self.generate(force=True)
            sync.assert_not_called()

    def test_profile_sync_failure_does_not_undo_valid_session(self):
        with patch('engine.shutil.which', return_value='/usr/bin/hyprixe-login-theme-sync'), \
             patch('engine.run', return_value=type('Result', (), {'returncode': 1, 'stderr': 'sync refused', 'stdout': ''})()), \
             contextlib.redirect_stderr(io.StringIO()) as errors:
            self.generate()
        self.assertIn('Login theme sync failed', errors.getvalue())
        self.assertEqual(self.engine.current_wallpaper.resolve(), self.image)
        self.assertEqual(self.engine.cache_status(self.engine.load_state()), 'valid')

    @unittest.skipUnless(shutil.which('jq'), 'startup helper monitor parsing needs jq')
    def test_real_startup_helper_uses_engine_for_persisted_and_absent_state(self):
        from test_runtime import MOCK
        bin_dir = self.root / 'mock-bin'; bin_dir.mkdir()
        for name in ('awww', 'awww-daemon', 'hyprctl', 'uwsm', 'systemctl', 'pgrep'):
            command = bin_dir / name
            command.write_text(MOCK); command.chmod(0o755)
        helper = self.root / '.local/bin/hyprixe-theme'
        helper.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / 'common/local/bin/hyprixe-theme', helper); helper.chmod(0o755)
        shutil.copytree(self.resources, self.engine.data / 'theme')
        (self.root / 'ready').touch()
        env = dict(os.environ, XDG_RUNTIME_DIR=str(self.root), XDG_CONFIG_HOME=str(ROOT / 'common/config'),
                   MOCK_ROOT=str(self.root), MOCK_UWSM='1', MOCK_GRAPHICAL='active', MOCK_SERVICE='enabled',
                   PATH=str(bin_dir) + os.pathsep + os.environ['PATH'])
        for selected in (self.image, None):
            with self.subTest(state=selected):
                if selected:
                    self.generate(enabled=False)
                else:
                    self.engine.state_file.unlink()
                    shutil.rmtree(self.engine.cache)
                (self.root / 'calls').unlink(missing_ok=True)
                result = subprocess.run(['bash', str(ROOT / 'common/config/hypr/scripts/Wallpaper.sh')],
                                        env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = [json.loads(line) for line in (self.root / 'calls').read_text().splitlines()]
                applied = [call for call in calls if call[:2] == ['awww', 'img']]
                self.assertEqual(len(applied), 1)
                self.assertEqual(applied[0][-1], str(selected or self.reference))
                self.assertEqual(self.engine.current_wallpaper.resolve(), selected or self.reference)
