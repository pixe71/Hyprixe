import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
from support import source_path, configure_imports, shell_bytes
configure_imports()

sys.path.insert(0, str(ROOT / 'scripts'))
from terminal_checks import check_config, config_errors, integration_errors, runtime_errors


class TerminalChecksTests(unittest.TestCase):
    def test_active_integration_uses_kitty(self):
        self.assertEqual(integration_errors(source_path(ROOT, '.config')), [])

    def test_stale_launcher_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'settings with spaces'
            shutil.copytree(source_path(ROOT, '.config'), config)
            (config / 'hypr/scripts/LaunchTerminal.sh').write_text('exec uwsm app -- alacritty "$@"\n')
            errors = integration_errors(config)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn('LaunchTerminal.sh', errors[0])

    def test_missing_configuration_fails_without_traceback(self):
        results = []
        check_config(lambda ok, msg: results.append((ok, msg)), ROOT / 'missing-kitty.conf')
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0][0])

    def test_missing_parser_is_explicitly_skipped(self):
        results = []
        output = io.StringIO()
        with patch('terminal_checks.shutil.which', return_value=None), contextlib.redirect_stdout(output):
            check_config(lambda ok, msg: results.append((ok, msg)), source_path(ROOT, '.config/kitty/kitty.conf'))
        self.assertTrue(results[0][0])  # File presence only; parsing is not claimed.
        self.assertIn('SKIPPED: native Kitty parser unavailable', output.getvalue())

    def test_missing_kitty_and_wrong_font_are_dependency_errors(self):
        with patch('terminal_checks.shutil.which', side_effect=lambda name: None if name == 'kitty' else '/bin/' + name), \
             patch('terminal_checks.subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'DejaVu Sans Mono', '')):
            errors = runtime_errors()
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(any('Kitty executable missing' in error for error in errors))
        self.assertTrue(any('JetBrains Mono font missing' in error for error in errors))

    @unittest.skipUnless(shutil.which('kitty'), 'native Kitty parser unavailable')
    def test_native_parser_accepts_real_config_without_display(self):
        self.assertEqual(config_errors(source_path(ROOT, '.config/kitty/kitty.conf')), [])

    @unittest.skipUnless(shutil.which('kitty'), 'native Kitty parser unavailable')
    def test_native_parser_rejects_bad_value_and_unknown_option(self):
        with tempfile.TemporaryDirectory(prefix='kitty parser with spaces ') as folder:
            config = Path(folder) / 'kitty.conf'
            for contents in ('background_opacity invalid\n', 'hyprixe_unknown_option yes\n'):
                with self.subTest(contents=contents):
                    config.write_text(contents)
                    self.assertTrue(config_errors(config))


if __name__ == '__main__':
    unittest.main()
