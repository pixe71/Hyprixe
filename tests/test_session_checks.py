import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('session_checks', ROOT / 'scripts/session_checks.py')
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)


class SessionChecks(unittest.TestCase):
    def inspect(self, managed=True, graphical='active', stale=False, failed_unit=None,
                external_agent=False, environment=None):
        reports, commands = [], []
        env = {'WAYLAND_DISPLAY': 'wayland-1', 'HYPRLAND_INSTANCE_SIGNATURE': 'test-instance'}
        if environment is not None:
            env = environment

        def runner(command, **kwargs):
            commands.append(command)
            code, output = 0, ''
            if command[0] == 'uwsm':
                code = 0 if managed else 1
            elif command[0] == 'pgrep':
                code = 0 if external_agent else 1
            elif command[-1] == 'show-environment':
                output = 'WAYLAND_DISPLAY=wayland-1\nHYPRLAND_INSTANCE_SIGNATURE=' + ('stale' if stale else 'test-instance') + '\nXDG_CURRENT_DESKTOP=Hyprland\n'
            elif 'graphical-session.target' in command:
                output = graphical + '\n'
            else:
                unit = command[3]
                output = 'ActiveState=failed\nResult=dependency\n' if unit == failed_unit else 'ActiveState=active\nResult=success\n'
            return subprocess.CompletedProcess(command, code, output, '')

        ok = session.check_session(lambda passed, message: reports.append((passed, message)),
                                   environ=env, runner=runner)
        # Diagnostics must never repair or alter the running session.
        self.assertFalse(any(word in command for command in commands
                             for word in ('start', 'stop', 'finalize', 'import-environment')))
        return ok, reports, commands

    def test_healthy_managed_session_and_all_services_pass(self):
        ok, reports, _ = self.inspect()
        self.assertTrue(ok)
        self.assertTrue(all(passed for passed, _ in reports))
        self.assertTrue(any('waybar.service' in message for _, message in reports))

    def test_plain_hyprland_with_imported_environment_is_not_uwsm(self):
        ok, reports, commands = self.inspect(managed=False, graphical='inactive')
        self.assertFalse(ok)
        self.assertTrue(any(not passed and 'Hyprland (uwsm-managed)' in message for passed, message in reports))
        self.assertFalse(any('waybar.service' in command for command in commands))

    def test_manually_active_graphical_target_does_not_replace_uwsm(self):
        ok, reports, _ = self.inspect(managed=False)
        self.assertFalse(ok)
        self.assertTrue(any(not passed and 'not managed by UWSM' in message for passed, message in reports))

    def test_inactive_graphical_target_reports_waybar_requisite(self):
        ok, reports, _ = self.inspect(graphical='inactive')
        self.assertFalse(ok)
        self.assertTrue(any(not passed and 'Requisite=' in message for passed, message in reports))

    def test_stale_manager_environment_is_reported(self):
        ok, reports, _ = self.inspect(stale=True)
        self.assertFalse(ok)
        self.assertTrue(any(not passed and 'stale' in message for passed, message in reports))

    def test_failed_waybar_service_reports_unit_result_and_journal_command(self):
        ok, reports, _ = self.inspect(failed_unit='waybar.service')
        self.assertFalse(ok)
        self.assertTrue(any(not passed and 'result=dependency' in message and 'journalctl' in message
                            for passed, message in reports))

    def test_existing_external_polkit_agent_is_accepted(self):
        ok, reports, _ = self.inspect(failed_unit='hyprixe-polkit.service', external_agent=True)
        self.assertTrue(ok)
        self.assertTrue(any('already running' in message for _, message in reports))

    def test_no_current_hyprland_environment_is_not_a_pass(self):
        ok, reports, commands = self.inspect(environment={})
        self.assertFalse(ok)
        self.assertFalse(commands)
        self.assertIn('terminal inside the session', reports[0][1])

    def test_unavailable_manager_produces_diagnostic_without_traceback(self):
        reports = []
        def unavailable(command, **kwargs):
            raise OSError('no user bus')
        ok = session.check_session(lambda passed, message: reports.append((passed, message)),
                                   environ={'WAYLAND_DISPLAY': 'wayland-1', 'HYPRLAND_INSTANCE_SIGNATURE': 'test'},
                                   runner=unavailable)
        self.assertFalse(ok)
        self.assertTrue(any(not passed for passed, _ in reports))


if __name__ == '__main__':
    unittest.main()
