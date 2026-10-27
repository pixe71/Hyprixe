"""Hardware-independent contracts for the native Frosted Glass bar."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import deploy
from waybar_checks import check_source

spec = importlib.util.spec_from_file_location('bar_temperature', ROOT / '.config/hypr/waybar/scripts/temperature.py')
sensor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sensor)


class SensorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe sensors ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def file(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        return path

    def test_intel_and_multiple_packages_are_discovered_without_an_index(self):
        self.file('class/hwmon/hwmon39/name', 'coretemp')
        self.file('class/hwmon/hwmon39/temp2_label', 'Package id 0')
        self.file('class/hwmon/hwmon39/temp2_input', '48000')
        self.file('class/hwmon/hwmon71/name', 'coretemp')
        self.file('class/hwmon/hwmon71/temp1_input', '51000')
        disk = Mock(side_effect=AssertionError('No disk fallback expected'))
        result = sensor.status(self.root, disk)
        self.assertEqual(result['class'], 'temperature')
        self.assertIn('51°C', result['text'])

    def test_amd_tctl_is_detected_without_a_cpu_model(self):
        self.file('class/hwmon/hwmon77/name', 'k10temp')
        self.file('class/hwmon/hwmon77/temp1_label', 'Tctl')
        self.file('class/hwmon/hwmon77/temp1_input', '62000')
        self.assertIn('62°C', sensor.status(self.root)['text'])

    def test_arm_thermal_zone_is_detected_by_type(self):
        self.file('class/thermal/thermal_zone42/type', 'cpu-thermal')
        self.file('class/thermal/thermal_zone42/temp', '43000')
        self.assertIn('43°C', sensor.status(self.root)['text'])

    def test_gpu_ssd_and_ambiguous_acpi_are_never_reported_as_cpu(self):
        for i, driver in enumerate(('amdgpu', 'nvme', 'acpitz')):
            self.file(f'class/hwmon/hwmon{i}/name', driver)
            self.file(f'class/hwmon/hwmon{i}/temp1_input', '90000')
        disk = Mock(return_value=(100, 42, 58))
        result = sensor.status(self.root, disk)
        self.assertEqual(result['class'], 'storage')
        self.assertIn('42%', result['text'])
        disk.assert_called_once_with('/')

    def test_invalid_out_of_range_and_removed_sensors_fall_back(self):
        self.file('class/hwmon/hwmon90/name', 'coretemp')
        path = self.file('class/hwmon/hwmon90/temp1_input', 'malformed')
        for value in ('malformed', '0', '999000', '-999000'):
            path.write_text(value)
            self.assertEqual(sensor.status(self.root, lambda _: (100, 25, 75))['class'], 'storage')
        path.unlink()
        self.assertEqual(sensor.status(self.root, lambda _: (100, 25, 75))['class'], 'storage')

    def test_fully_unavailable_hardware_returns_valid_waybar_json(self):
        result = sensor.status(self.root, Mock(side_effect=OSError('unavailable')))
        self.assertEqual(json.loads(json.dumps(result))['class'], 'unavailable')

    def test_kernel_labels_are_escaped_for_tooltip_markup(self):
        self.file('class/hwmon/hwmon9/name', 'other&driver')
        self.file('class/hwmon/hwmon9/temp1_label', 'CPU & socket')
        self.file('class/hwmon/hwmon9/temp1_input', '42000')
        self.assertIn('&amp;', sensor.status(self.root)['tooltip'])


def css_rules(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return [(set(s.strip() for s in selectors.split(',')),
             {k.strip(): v.strip() for part in body.split(';') if ':' in part for k, v in [part.split(':', 1)]})
            for selectors, body in re.findall(r'([^{}]+)\{([^{}]+)\}', text)]


class LayoutTests(unittest.TestCase):
    def test_missing_active_asset_aborts_scoped_deployment_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder) / 'home'; home.mkdir()
            roots = {key: home / key for key in ('config', 'data', 'state')}
            source = Path(folder) / 'incomplete source'
            with patch('deploy.REPO', source):
                with self.assertRaises(FileNotFoundError):
                    deploy.install(home, roots, 'native', waybar_only=True)
            self.assertEqual(list(home.iterdir()), [])

    def test_workspace_filter_shows_only_one_to_four_without_changing_hyprland(self):
        config = json.loads((ROOT / '.config/hypr/waybar/configs/Frosted-Glass').read_text())
        ignored = config['hyprland/workspaces']['ignore-workspaces'][0]
        self.assertTrue(all(re.fullmatch(ignored, str(i)) is None for i in range(1, 5)))
        self.assertTrue(all(re.fullmatch(ignored, name) for name in ('5', '10', '42', 'notes', 'special:term')))

    def test_every_original_frosted_css_rule_is_preserved(self):
        original = css_rules((ROOT / 'tests/fixtures/waybar-frosted-original.css').read_text())
        current = css_rules((ROOT / '.config/hypr/waybar/style/Frosted-Glass.css').read_text())
        for selectors, declarations in original:
            self.assertTrue(any(selectors <= found and values == declarations for found, values in current), selectors)

    def test_source_contract_and_no_duplicate_modules(self):
        results = []
        check_source(lambda ok, label: results.append((ok, label)), ROOT)
        self.assertTrue(all(ok for ok, _ in results), results)
        config = json.loads((ROOT / '.config/hypr/waybar/configs/Frosted-Glass').read_text())
        modules = sum((config['modules-' + key] for key in ('left', 'center', 'right')), [])
        modules += config['group/traygroup']['modules']
        self.assertEqual(len(modules), len(set(modules)))
        self.assertNotIn('locale', config['clock#date'], 'A missing system locale must not disable the date module')
        self.assertEqual(config['custom/power']['on-click'], '"${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/PowerMenu.sh"')

    def test_missing_layout_reports_failure_without_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            results = []
            check_source(lambda ok, label: results.append((ok, label)), folder)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0][0])

    def test_scoped_deployment_backup_repeat_and_restore_preserve_other_apps(self):
        with tempfile.TemporaryDirectory(prefix='hyprixe bar deployment ') as folder:
            home = Path(folder)
            roots = {key: home / value for key, value in (('config', 'settings with spaces'), ('data', 'data'), ('state', 'state'))}
            personal = roots['config'] / 'hypr/waybar/personal.css'
            personal.parent.mkdir(parents=True); personal.write_text('personal')
            dolphin = roots['config'] / 'dolphinrc'; dolphin.write_text('personal Dolphin')
            old = roots['config'] / 'hypr/waybar/configs/Frosted-Glass'
            old.parent.mkdir(); old.write_text('old bar')
            with contextlib.redirect_stdout(io.StringIO()):
                backup = deploy.install(home, roots, 'native', waybar_only=True)
                self.assertEqual(deploy.read_manifest(backup)['scope'], 'waybar')
                self.assertIsNone(deploy.install(home, roots, 'native', waybar_only=True))
                self.assertTrue((roots['data'] / 'fonts/hyprixe/HyprixeDebian.ttf').is_file())
                deploy.restore(backup, home)
            self.assertEqual(old.read_text(), 'old bar')
            self.assertEqual(personal.read_text(), 'personal')
            self.assertEqual(dolphin.read_text(), 'personal Dolphin')
            self.assertFalse((roots['config'] / 'hypr/profile.lua').exists())

    def test_scoped_dry_run_and_incompatible_flags_do_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            roots = {key: home / key for key in ('config', 'data', 'state')}
            with contextlib.redirect_stdout(io.StringIO()):
                deploy.install(home, roots, 'native', waybar_only=True, dry=True)
            self.assertEqual(list(home.iterdir()), [])
        result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--waybar-only', '--dolphin-only'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
