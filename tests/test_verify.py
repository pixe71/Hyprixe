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


class SourceTreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-source-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.waybar = self.root / '.config/hypr/waybar'
        for name in ('configs/Frosted-Glass', 'style.css', 'style/Frosted-Glass.css'):
            path = self.waybar / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture')

    def check_sources(self):
        output = io.StringIO()
        with patch.object(verify, 'failed', 0), contextlib.redirect_stdout(output):
            ok = verify.check_source_tree(self.root, list(self.root.rglob('*')))
            failures = verify.failed
        return ok, failures, output.getvalue()

    def test_intact_sources_pass(self):
        ok, failures, output = self.check_sources()
        self.assertTrue(ok, output)
        self.assertEqual(failures, 0)

    def test_dangling_symlink_is_detected_even_though_is_file_is_false(self):
        css = self.waybar / 'style.css'
        css.unlink()
        css.symlink_to('@import "style/Frosted-Glass.css";')
        self.assertFalse(css.is_file())
        ok, failures, output = self.check_sources()
        self.assertFalse(ok)
        self.assertGreater(failures, 0)
        self.assertIn('Broken source symlink: .config/hypr/waybar/style.css', output)

    def test_missing_css_is_a_source_failure(self):
        (self.waybar / 'style/Frosted-Glass.css').unlink()
        ok, failures, output = self.check_sources()
        self.assertFalse(ok)
        self.assertEqual(failures, 1)
        self.assertIn('Required Waybar source file missing:', output)


class OriginalAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-assets-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('docs/inventory-original.tsv', 'wallpapers/min_forest.jpg',
                     '.config/Kvantum/Frosted-Glass/Frosted-Glass.svg',
                     '.config/Kvantum/Frosted-Glass/Frosted-Glass.kvconfig',
                     '.local/share/kxmlgui5/dolphin/dolphinui.rc'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)

    def check_assets(self):
        output = io.StringIO()
        with patch.object(verify, 'failed', 0), contextlib.redirect_stdout(output):
            verify.check_original_assets(self.root)
            failures = verify.failed
        return failures, output.getvalue()

    def test_original_bytes_pass(self):
        failures, output = self.check_assets()
        self.assertEqual(failures, 0, output)
        self.assertEqual(output.count('PASS:'), 3)

    def test_changed_asset_reports_its_path_and_hashes(self):
        path = self.root / '.config/Kvantum/Frosted-Glass/Frosted-Glass.kvconfig'
        path.write_bytes(path.read_bytes() + b'changed')
        failures, output = self.check_assets()
        self.assertEqual(failures, 1)
        self.assertIn('FAIL: Original asset SHA256: .config/Kvantum/Frosted-Glass/Frosted-Glass.kvconfig', output)
        self.assertIn('expected ', output)
        self.assertIn('got ', output)

    def test_missing_asset_reports_failure_and_checks_the_others(self):
        (self.root / 'wallpapers/min_forest.jpg').unlink()
        failures, output = self.check_assets()
        self.assertEqual(failures, 1)
        self.assertIn('FAIL: Original asset: wallpapers/min_forest.jpg:', output)
        self.assertEqual(output.count('PASS:'), 2)


if __name__ == '__main__':
    unittest.main()
