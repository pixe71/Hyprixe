"""Version eligibility must agree at installation and in the live audit."""
import contextlib
import io
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
from support import source_path, configure_imports, shell_bytes
configure_imports()

sys.path.insert(0, str(ROOT / 'scripts'))
from hyprland_version import assess, MINIMUM, REVIEWED_RELEASES


class PolicyTests(unittest.TestCase):
    def test_reviewed_reference_releases_are_explicit(self):
        self.assertEqual(MINIMUM, (0, 55, 2))
        self.assertEqual(REVIEWED_RELEASES, {(0, 55, 2), (0, 56, 2)})
        for version in ('0.55.2', 'v0.56.2', '0.55.2+ds-1~bpo13+1'):
            with self.subTest(version=version):
                result = assess('Hyprland ' + version + ' built from branch fixture')
                self.assertTrue(result.allowed)
                self.assertTrue(result.reviewed)
                self.assertEqual(result.warning, '')

    def test_later_versions_are_eligible_without_claiming_validation(self):
        for version in ('0.55.3', '0.56.0', '0.56.3', '0.57.0', '1.0.0',
                        '0.56.2-rc1', '0.56.2+dirty', '0.57.0-dev'):
            with self.subTest(version=version):
                result = assess('Hyprland ' + version)
                self.assertTrue(result.allowed)
                self.assertFalse(result.reviewed)
                self.assertIn('provisional', result.warning)

    def test_old_unknown_or_failed_queries_are_rejected(self):
        for output, code in (('Hyprland 0.55.1', 0), ('Hyprland 0.54.9', 0),
                             ('Hyprland 0.55.2-rc1', 0),
                             ('Hyprland 0.55', 0), ('dependency 0.56.2', 0),
                             ('Hyprland 0.56.2broken', 0), ('', 0),
                             ('Hyprland 0.56.2', 1)):
            with self.subTest(output=output, code=code):
                self.assertFalse(assess(output, code).allowed)

    def test_optional_calculator_uses_the_debian_cli_package(self):
        packages = [line.split('#', 1)[0].strip() for line in
                    (source_path(ROOT, 'packages-optional.txt')).read_text().splitlines()]
        self.assertIn('qalc', packages)
        self.assertNotIn('qalculate', packages)
        self.assertIn('qalc', (source_path(ROOT, '.config/hypr/UserScripts/RofiCalc.sh')).read_text())


class InstallPolicyTests(unittest.TestCase):
    PLATFORM = 'debian'
    def preflight(self, output, code=0):
        stream = io.StringIO()
        with contextlib.ExitStack() as stack:
            for name in ('waybar_compat.has_lua_workspace_ipc', 'waybar_compat.has_wlr_taskbar',
                         'waybar_compat.has_click_drawer', 'rofi_compat.has_wayland_support',
                         'rofi_launcher.has_launcher_actions', 'rofi_launcher.has_launcher_cover'):
                stack.enter_context(patch(name, return_value=True))
            for name in ('dolphin_checks.runtime_errors', 'terminal_checks.runtime_errors',
                         'terminal_checks.config_errors', 'wlogout_checks.runtime_errors',
                         'interactive_shell.dependencies'):
                stack.enter_context(patch(name, return_value=[]))
            stack.enter_context(patch('shutil.which', side_effect=lambda c: '/bin/' + c))
            stack.enter_context(patch('pathlib.Path.is_file', return_value=True))
            stack.enter_context(patch('pathlib.Path.glob', return_value=[Path('/fixture/libkvantum.so')]))
            stack.enter_context(patch('subprocess.run', return_value=
                                     subprocess.CompletedProcess([], code, output, '')))
            stack.enter_context(contextlib.redirect_stdout(stream))
            stack.enter_context(contextlib.redirect_stderr(stream))
            try:
                runpy.run_path(str(source_path(ROOT, 'scripts/check-deps.py')), run_name='__main__')
                status = 0
            except SystemExit as exc:
                status = exc.code
        return status, stream.getvalue()

    def test_install_and_shared_policy_agree_for_reference_future_old_and_unknown(self):
        for text in ('Hyprland 0.55.2', 'Hyprland 0.56.2', 'Hyprland 0.57.0',
                     'Hyprland 1.0.0', 'Hyprland 0.55.1', 'unknown version'):
            with self.subTest(text=text):
                code, output = self.preflight(text)
                policy = assess(text)
                self.assertEqual(code == 0, policy.allowed, output)
                if policy.warning:
                    self.assertIn('WARNING:', output)
                    self.assertIn('provisional', output)

    def test_failed_version_command_is_a_preflight_failure(self):
        code, output = self.preflight('Hyprland 0.56.2', 1)
        self.assertEqual(code, 1)
        self.assertIn('command failed', output)


if __name__ == '__main__':
    unittest.main()
