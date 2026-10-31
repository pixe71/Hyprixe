import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
from support import source_path, configure_imports, shell_bytes
configure_imports()

spec = importlib.util.spec_from_file_location('rofi_compat', source_path(ROOT, 'scripts/rofi_compat.py'))
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)


class RofiCapabilityTests(unittest.TestCase):
    def test_wayland_builds_are_detected_without_a_working_display(self):
        for info, version in (('wayland enabled', 'Version: 2.0.0'),
                              ('wayland: enabled (selected)', 'Version: 2.0.0'),
                              ('', 'Version: 1.7.9+wayland')):
            with self.subTest(info=info, version=version):
                results = [subprocess.CompletedProcess([], 1, '', info),
                           subprocess.CompletedProcess([], 0, version, '')]
                with patch.object(compat.subprocess, 'run', side_effect=results):
                    self.assertTrue(compat.has_wayland_support('/example/rofi'))

    def test_x11_only_rofi_is_not_mistaken_for_a_theme_failure(self):
        results = [subprocess.CompletedProcess([], 1, '', 'Failed to open display'),
                   subprocess.CompletedProcess([], 0, 'Version: 1.7.5', '')]
        with patch.object(compat.subprocess, 'run', side_effect=results):
            self.assertFalse(compat.has_wayland_support('/example/rofi'))

    def test_missing_executable_is_not_supported(self):
        with patch.object(compat.shutil, 'which', return_value=None):
            self.assertFalse(compat.has_wayland_support())

    def test_failed_or_stalled_probe_is_not_supported(self):
        for error in (OSError('not executable'), subprocess.TimeoutExpired('rofi', 10)):
            with self.subTest(error=type(error).__name__):
                with patch.object(compat.subprocess, 'run', side_effect=error):
                    self.assertFalse(compat.has_wayland_support('/example/rofi'))


if __name__ == '__main__':
    unittest.main()
