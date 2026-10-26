import contextlib
import importlib.util
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verify', ROOT / 'scripts/verify.py')
verify = importlib.util.module_from_spec(spec)
with patch.object(sys, 'path', [str(ROOT / 'scripts'), *sys.path]):
    spec.loader.exec_module(verify)


class ConfigurationFormatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-verify-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in (
            '.config/alacritty/alacritty.toml',
            '.config/hypr/waybar/configs/Frosted-Glass',
            '.config/Kvantum/Frosted-Glass/Frosted-Glass.svg',
            '.local/share/kxmlgui5/dolphin/dolphinui.rc',
        ):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def check_formats(self):
        output = io.StringIO()
        with patch.object(verify, 'failed', 0), contextlib.redirect_stdout(output):
            verify.check_configuration_formats(self.root)
            failures = verify.failed
        return failures, output.getvalue()

    def test_active_files_pass_without_legacy_waybar_wrapper(self):
        self.assertFalse((self.root / '.config/hypr/waybar/config').exists())
        failures, output = self.check_formats()
        self.assertEqual(failures, 0, output)
        self.assertEqual(output.count('PASS:'), 4)

    def test_missing_active_waybar_config_reports_failure_and_continues(self):
        (self.root / '.config/hypr/waybar/configs/Frosted-Glass').unlink()
        failures, output = self.check_formats()
        self.assertEqual(failures, 1)
        self.assertIn('FAIL: Waybar JSON: .config/hypr/waybar/configs/Frosted-Glass', output)
        self.assertEqual(output.count('PASS:'), 3)
        self.assertIn('PASS: Dolphin XML:', output)

    def test_invalid_active_waybar_json_reports_failure_and_continues(self):
        (self.root / '.config/hypr/waybar/configs/Frosted-Glass').write_text('{ invalid JSON')
        failures, output = self.check_formats()
        self.assertEqual(failures, 1)
        self.assertIn('FAIL: Waybar JSON:', output)
        self.assertEqual(output.count('PASS:'), 3)

    def test_invalid_toml_and_xml_are_reported_without_aborting(self):
        (self.root / '.config/alacritty/alacritty.toml').write_text('broken = [')
        (self.root / '.config/Kvantum/Frosted-Glass/Frosted-Glass.svg').write_text('<svg>')
        failures, output = self.check_formats()
        self.assertEqual(failures, 2)
        self.assertIn('FAIL: Alacritty TOML:', output)
        self.assertIn('FAIL: Kvantum SVG:', output)
        self.assertEqual(output.count('PASS:'), 2)
        self.assertIn('PASS: Dolphin XML:', output)


if __name__ == '__main__':
    unittest.main()
