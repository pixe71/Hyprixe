import contextlib
import io
import os
from pathlib import Path
import shutil
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import deploy
import rofi_launcher as launcher
import rofi_checks as checks
from rofi_compat import has_wayland_support


class RofiPreparationTests(unittest.TestCase):
    def source_fixture(self, root):
        for name, original, _ in launcher.PATCHES:
            path = root / name
            path.parent.mkdir(exist_ok=True, parents=True)
            with path.open('a') as output:
                output.write('before\n' + original + '\nafter\n')

    def test_pinned_source_patch_is_idempotent_and_gated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source/rofi.c'
            self.source_fixture(root)
            launcher.patch_source(root)
            first = source.read_bytes()
            launcher.patch_source(root)
            self.assertEqual(source.read_bytes(), first)
            text = first.decode()
            self.assertIn('find_arg("-hyprixe-launcher") >= 0', text)
            self.assertIn('hyprixe_action >= 16 && hyprixe_action <= 18', text)
            self.assertIn('rofi_set_return_code(10 + hyprixe_action - 16)', text)
            self.assertIn('retv = mode_result(sw, mretv, &input, selected_line);', text)
            hover = (root / 'source/view.c').read_text()
            self.assertIn('widget_set_state(target, "hover")', hover)
            self.assertIn('find_arg("-hyprixe-launcher") >= 0', hover)

    def test_unknown_or_ambiguous_source_is_rejected_without_writes(self):
        for text in ('unknown source', launcher.ORIGINAL * 2, launcher.MARKER + launcher.ORIGINAL):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / 'source/rofi.c'
                self.source_fixture(root)
                source.write_text(text)
                with self.assertRaisesRegex(ValueError, 'Unsupported Rofi source'):
                    launcher.patch_source(root)
                self.assertEqual(source.read_text(), text)

    def test_launcher_capability_requires_actual_binary_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'rofi'
            self.assertFalse(launcher.has_launcher_actions(binary))
            binary.write_bytes(b'Wayland enabled')
            self.assertFalse(launcher.has_launcher_actions(binary))
            binary.write_bytes(b'\x7fELF\0' + launcher.MARKER.encode() + b'\0')
            self.assertTrue(launcher.has_launcher_actions(binary))
            self.assertFalse(launcher.has_launcher_actions(None))

    def test_late_patch_mismatch_does_not_partially_modify_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root)
            (root / 'source/wayland/display.c').write_text('unsupported backend')
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with self.assertRaisesRegex(ValueError, 'Unsupported Rofi source'):
                launcher.patch_source(root)
            self.assertEqual({p: p.read_bytes() for p in before}, before)

    @unittest.skipUnless(shutil.which('rofi') and has_wayland_support(), 'native Wayland Rofi parser required')
    def test_native_rasi_parser_preserves_separate_icon_and_action_properties(self):
        result = subprocess.run(['rofi', '-config', str(ROOT / '.config/hypr/rofi/config-launcher.rasi'),
                                 '-dump-theme'], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, glyph, action in (('applications', '', 1), ('files', '', 17),
                                    ('windows', '', 18), ('terminal', '', 19)):
            with self.subTest(button=name):
                block = re.search(r'\bbutton-' + name + r'\s*\{(.*?)\n\}', result.stdout, re.S)
                self.assertIsNotNone(block)
                self.assertRegex(block[1], r'str:\s*"' + glyph + r'";\s*\n')
                self.assertRegex(block[1], r'action:\s*"kb-custom-' + str(action) + r'";')


class RofiDeploymentTests(unittest.TestCase):
    def test_source_contract_and_missing_helper_diagnostic(self):
        self.assertEqual(checks.source_errors(ROOT), [])
        with tempfile.TemporaryDirectory() as tmp:
            failures = checks.source_errors(Path(tmp))
            self.assertTrue(any('WindowSwitcher.sh' in x for x in failures))

    def test_custom_xdg_wallpaper_repeat_restore_preserves_other_menus(self):
        with tempfile.TemporaryDirectory(prefix='hyprixe-rofi-test-') as tmp:
            home = Path(tmp) / 'home with spaces'
            home.mkdir()
            roots = {kind: home / folder for kind, folder in (
                ('config', 'settings with spaces'), ('data', 'data with spaces'), ('state', 'state'))}
            env = dict(HOME=str(home), XDG_CONFIG_HOME=str(roots['config']),
                       XDG_DATA_HOME=str(roots['data']), XDG_STATE_HOME=str(roots['state']))
            script = roots['config'] / 'hypr/scripts/RofiLauncher.sh'
            script.parent.mkdir(parents=True)
            script.write_text('# previous launcher\n')
            script.chmod(0o640)
            with patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()):
                deploy.install(home, roots, 'native')
                backups = sorted((roots['state'] / 'hyprixe/backups').iterdir())
                deploy.install(home, roots, 'native')
                self.assertEqual(sorted((roots['state'] / 'hyprixe/backups').iterdir()), backups)
                results = []
                checks.check_installed(lambda ok, message: results.append((ok, message)))
                self.assertTrue(all(ok for ok, _ in results), results)
                theme = (roots['config'] / 'hypr/rofi' / checks.OVERLAY).read_text()
                self.assertIn(str(roots['data'] / 'hyprixe/wallpapers/min_forest.jpg'), theme)
                self.assertNotIn('$HOME', theme)
                for name in ('config.rasi', '0-shared-fonts.rasi', 'themes/Frosted-Glass.rasi',
                             'wallust/colors-rofi.rasi'):
                    self.assertEqual((roots['config'] / 'hypr/rofi' / name).read_bytes(),
                                     (ROOT / '.config/hypr/rofi' / name).read_bytes())
                (roots['data'] / 'hyprixe/wallpapers/min_forest.jpg').unlink()
                results.clear()
                checks.check_installed(lambda ok, message: results.append((ok, message)))
                self.assertFalse(results[0][0])
                self.assertIn('Missing wallpaper', results[0][1])
                # Restore expects the installed assets intact; put back the test deletion.
                shutil.copyfile(ROOT / 'wallpapers/min_forest.jpg',
                                roots['data'] / 'hyprixe/wallpapers/min_forest.jpg')
                deploy.restore(backups[0], home)
                self.assertEqual(script.read_text(), '# previous launcher\n')
                self.assertEqual(script.stat().st_mode & 0o777, 0o640)
                self.assertFalse((roots['config'] / 'hypr/rofi/config-launcher.rasi').exists())

    def test_missing_installed_configuration_reports_failure_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, XDG_CONFIG_HOME=tmp):
            results = []
            checks.check_installed(lambda ok, message: results.append((ok, message)))
            self.assertFalse(results[0][0])
            self.assertIn('config-launcher.rasi', results[0][1])
