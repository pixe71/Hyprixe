import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
from support import source_path, configure_imports, shell_bytes
configure_imports()

SCRIPTS = source_path(ROOT, '.config/hypr/scripts')
MOCK = '''#!/usr/bin/python3
import json, os, pathlib, sys
name=pathlib.Path(sys.argv[0]).name
root=pathlib.Path(os.environ['MOCK_ROOT'])
with (root/'calls').open('a') as f: f.write(json.dumps([name]+sys.argv[1:])+'\\n')
if name=='hyprctl':
    if sys.argv[1]=='monitors':
        if os.environ.get('MOCK_MONITORS_DELAYED') and not (root/'monitors-polled').exists():
            (root/'monitors-polled').touch()
            print('[]')
        else: print('[{"name":"DP-3"},{"name":"eDP-2"}]')
    elif sys.argv[1]=='clients':
        print(os.environ.get('MOCK_CLIENTS', '[{"mapped":true,"address":"0xabc","class":"kitty","title":"Example"}]'))
    elif sys.argv[1]=='dispatch':
        print(os.environ.get('MOCK_DISPATCH_RESULT', 'ok'))
elif name=='awww' and sys.argv[1]=='query':
    if os.environ.get('MOCK_NEVER_READY') or not (root/'ready').exists(): sys.exit(1)
    print('DP-3: 2560x1440, scale: 1, currently displaying: image\\neDP-2: 1920x1080')
elif name=='awww-daemon': (root/'ready').touch()
elif name=='rofi':
    if os.environ.get('MOCK_CANCEL'): sys.exit(1)
    if os.environ.get('MOCK_ROFI_FAILURE'): sys.exit(17)
    print(os.environ.get('MOCK_CHOICE',os.environ.get('MOCK_INDEX','0')))
    sys.exit(int(os.environ.get('MOCK_ROFI_STATUS', '0')))
elif name=='uwsm':
    if '-hyprixe-launcher' in sys.argv:
        sys.exit(int(os.environ.get('MOCK_LAUNCHER_STATUS', '0')))
    if sys.argv[1:]==['check','is-active','compositor-only']:
        sys.exit(0 if os.environ.get('MOCK_UWSM')=='1' else 1)
elif name=='systemctl':
    if 'is-active' in sys.argv and 'graphical-session.target' in sys.argv:
        sys.exit(0 if os.environ.get('MOCK_GRAPHICAL')=='active' else 1)
    if 'is-enabled' in sys.argv or 'is-active' in sys.argv:
        sys.exit(0 if os.environ.get('MOCK_SERVICE')=='enabled' else 1)
    if 'start' in sys.argv and 'hyprixe-awww.service' in sys.argv:
        (root/'ready').touch()
elif name=='pgrep': sys.exit(1)
'''


@unittest.skipUnless(shutil.which('jq'), 'jq required for runtime script mocks')
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-runtime-test-')
        self.root = Path(self.temp.name)
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        for name in ('hyprctl', 'awww', 'awww-daemon', 'rofi', 'sleep', 'systemctl', 'pgrep', 'waybar', 'uwsm'):
            p = bin_dir / name
            p.write_text(MOCK)
            p.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.root), XDG_RUNTIME_DIR=str(self.root),
                        XDG_CONFIG_HOME=str(source_path(ROOT, '.config')), XDG_DATA_HOME=str(self.root / 'data'),
                        XDG_STATE_HOME=str(self.root / 'state'), MOCK_ROOT=str(self.root),
                        PATH=str(bin_dir) + ':' + os.environ['PATH'])
        wallpaper = self.root / 'data/hyprixe/wallpapers/min_forest.jpg'
        wallpaper.parent.mkdir(parents=True)
        wallpaper.write_bytes(b'wallpaper fixture')

    def tearDown(self): self.temp.cleanup()

    def run_script(self, name, *args):
        return subprocess.run(['bash', str(SCRIPTS / name), *args], env=self.env, capture_output=True, text=True, timeout=15)

    def calls(self):
        return [json.loads(line) for line in (self.root / 'calls').read_text().splitlines()]

    def test_wallpaper_reuses_daemon_and_applies_to_all_outputs(self):
        (self.root / 'ready').touch()
        r = self.run_script('Wallpaper.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.calls()
        self.assertFalse(any(c[0] == 'awww-daemon' for c in calls))
        img = next(c for c in calls if c[:2] == ['awww', 'img'])
        self.assertEqual(img[img.index('--transition-type') + 1], 'none')
        self.assertNotIn('--transition-duration', img)
        self.assertNotIn('--outputs', img)
        self.assertNotIn('-o', img)
        self.assertEqual(img[-1], str(self.root / 'data/hyprixe/wallpapers/min_forest.jpg'))

    def test_wallpaper_starts_missing_daemon_only_once(self):
        r = self.run_script('Wallpaper.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sum(c[0] == 'awww-daemon' for c in self.calls()), 1)

    def test_wallpaper_failure_is_bounded_and_nonzero(self):
        self.env['MOCK_NEVER_READY'] = '1'
        r = self.run_script('Wallpaper.sh')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('not ready', r.stderr)
        self.assertEqual(sum(c[0] == 'awww-daemon' for c in self.calls()), 1)
        self.assertFalse(any(c[:2] == ['awww', 'img'] for c in self.calls()))

    def test_wallpaper_retries_only_until_initial_monitor_ipc_is_ready(self):
        self.env['MOCK_MONITORS_DELAYED'] = '1'
        (self.root / 'ready').touch()
        r = self.run_script('Wallpaper.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sum(c[:2] == ['hyprctl', 'monitors'] for c in self.calls()), 2)
        self.assertEqual(sum(c[0] == 'sleep' for c in self.calls()), 1)
        self.assertTrue(any(c[:2] == ['awww', 'img'] for c in self.calls()))

    def test_switcher_uses_one_snapshot_and_valid_address(self):
        r = self.run_script('WindowSwitcher.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.calls()
        self.assertEqual(sum(c[:2] == ['hyprctl', 'clients'] for c in calls), 1)
        dispatch = next(c for c in calls if c[:2] == ['hyprctl', 'dispatch'])
        self.assertIn('address:0xabc', dispatch[2])

    def test_switcher_cancel_is_a_noop(self):
        self.env['MOCK_CANCEL'] = '1'
        self.assertEqual(self.run_script('WindowSwitcher.sh').returncode, 0)
        self.assertFalse(any(c[:2] == ['hyprctl', 'dispatch'] for c in self.calls()))

    def test_switcher_lua_error_with_zero_exit_is_not_success(self):
        self.env['MOCK_DISPATCH_RESULT'] = 'Lua error: unsupported dispatcher'
        result = self.run_script('WindowSwitcher.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('focus failed', result.stderr)

    def test_switcher_rofi_failure_is_not_a_successful_cancel(self):
        self.env['MOCK_ROFI_FAILURE'] = '1'
        result = self.run_script('WindowSwitcher.sh')
        self.assertEqual(result.returncode, 17)
        self.assertIn('rofi failed', result.stderr)
        self.assertFalse(any(c[:2] == ['hyprctl', 'dispatch'] for c in self.calls()))

    def test_switcher_selects_one_of_multiple_windows_of_same_application(self):
        self.env['MOCK_CLIENTS'] = json.dumps([
            {'mapped': True, 'hidden': True, 'address': '0x000', 'class': 'Hidden', 'title': 'skip'},
            {'mapped': True, 'address': '0xabc', 'class': 'kitty', 'title': 'first'},
            {'mapped': True, 'address': '0xdef', 'class': 'kitty', 'title': 'second\nline'},
        ])
        self.env['MOCK_INDEX'] = '1'
        result = self.run_script('WindowSwitcher.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        dispatch = next(c for c in self.calls() if c[:2] == ['hyprctl', 'dispatch'])
        self.assertIn('hl.dsp.focus({ window = "address:0xdef" })', dispatch[2])
        self.assertIn('hl.dsp.window.alter_zorder({ mode = "top", window = "address:0xdef" })', dispatch[2])
        self.assertEqual(sum(c[:2] == ['hyprctl', 'clients'] for c in self.calls()), 1)

    def test_switcher_rejects_invalid_address_without_dispatch(self):
        self.env['MOCK_CLIENTS'] = '[{"mapped":true,"address":"bad; os.execute()","class":"test","title":"test"}]'
        result = self.run_script('WindowSwitcher.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c[:2] == ['hyprctl', 'dispatch'] for c in self.calls()))

    def test_switcher_prefers_managed_rofi(self):
        managed = self.root / '.local/bin/rofi'
        managed.parent.mkdir(parents=True)
        managed.write_text(MOCK.replace("name=pathlib.Path(sys.argv[0]).name", "name='rofi-managed'")
                           + "\nif name=='rofi-managed': print('0')\n")
        managed.chmod(0o755)
        result = self.run_script('WindowSwitcher.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(c[0] == 'rofi-managed' for c in self.calls()))
        self.assertFalse(any(c[0] == 'rofi' for c in self.calls()))

    def test_switcher_invalid_index_fails_without_dispatch(self):
        self.env['MOCK_INDEX'] = '999'
        self.assertNotEqual(self.run_script('WindowSwitcher.sh').returncode, 0)
        self.assertFalse(any(c[:2] == ['hyprctl', 'dispatch'] for c in self.calls()))

    def test_switcher_sidebar_closes_before_reusing_existing_app_helpers(self):
        settings = self.root / 'settings with spaces'
        shutil.copytree(source_path(ROOT, '.config/hypr'), settings / 'hypr')
        self.env['XDG_CONFIG_HOME'] = str(settings)
        for status, expected in ((26, ['uwsm', 'app', '--', 'dolphin']),
                                 (28, ['uwsm', 'app', '--', 'kitty']), (10, None)):
            with self.subTest(status=status):
                (self.root / 'calls').write_text('')
                self.env['MOCK_ROFI_STATUS'] = str(status)
                result = self.run_script('WindowSwitcher.sh')
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.calls()
                self.assertFalse(any(c[:2] == ['hyprctl', 'dispatch'] for c in calls))
                self.assertEqual(sum(c[:2] == ['hyprctl', 'clients'] for c in calls), 1)
                if expected:
                    self.assertEqual(calls[-1], expected)
                else:
                    self.assertIn(str(settings / 'hypr/rofi/config-launcher.rasi'), calls[-1])

    def test_switcher_unknown_custom_status_does_not_focus_a_window(self):
        self.env['MOCK_ROFI_STATUS'] = '27'
        result = self.run_script('WindowSwitcher.sh')
        self.assertEqual(result.returncode, 27)
        self.assertFalse(any(c[:2] == ['hyprctl', 'dispatch'] for c in self.calls()))

    def test_waybar_uses_vendor_service_even_if_not_enabled(self):
        self.env.update(MOCK_UWSM='1', MOCK_GRAPHICAL='active')
        r = self.run_script('WaybarStartup.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.calls()
        self.assertTrue(any(c[:3] == ['systemctl', '--user', 'start'] for c in calls))
        self.assertFalse(any(c[0] == 'waybar' for c in calls))

    def test_waybar_rejects_unmanaged_or_inactive_sessions_without_bypass(self):
        for managed, graphical in (('0', 'inactive'), ('0', 'active'), ('1', 'inactive')):
            with self.subTest(managed=managed, graphical=graphical):
                (self.root / 'calls').write_text('')
                self.env.update(MOCK_UWSM=managed, MOCK_GRAPHICAL=graphical)
                r = self.run_script('WaybarStartup.sh')
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('Hyprland (uwsm-managed)', r.stderr)
                self.assertFalse(any('start' in c or c[0] == 'waybar' for c in self.calls()))

    def test_waybar_custom_xdg_still_uses_managed_service(self):
        settings = self.root / 'settings with spaces'
        hypr = settings / 'hypr'
        shutil.copytree(source_path(ROOT, '.config/hypr'), hypr)
        # The launcher must work when no legacy include wrapper is installed.
        (hypr / 'waybar/config').unlink(missing_ok=True)
        self.env['XDG_CONFIG_HOME'] = str(settings)
        self.env.update(MOCK_UWSM='1', MOCK_GRAPHICAL='active')
        r = subprocess.run(['bash', str(hypr / 'scripts/WaybarStartup.sh')],
                           env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(['systemctl', '--user', 'start', 'waybar.service'], self.calls())
        self.assertFalse(any(c[0] == 'waybar' for c in self.calls()))

    def test_session_startup_finalizes_before_queuing_services(self):
        self.env['MOCK_UWSM'] = '1'
        r = self.run_script('SessionStartup.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.calls()
        finalize = next(i for i, c in enumerate(calls) if c[:2] == ['uwsm', 'finalize'])
        reload_units = calls.index(['systemctl', '--user', 'daemon-reload'])
        start = calls.index(['systemctl', '--user', 'start', '--no-block', 'hyprixe-session.target'])
        self.assertLess(finalize, start)
        self.assertLess(reload_units, finalize)
        self.assertIn('HYPRLAND_INSTANCE_SIGNATURE', calls[finalize])
        self.assertFalse(any('start' in c and 'graphical-session.target' in c for c in calls))
        self.assertFalse(any(c[0] in ('awww-daemon', 'waybar') for c in calls))

    def test_session_startup_rejects_plain_hyprland(self):
        r = self.run_script('SessionStartup.sh')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Hyprland (uwsm-managed)', (self.root / 'state/hyprixe/session.log').read_text())
        self.assertFalse(any(c[0] == 'systemctl' for c in self.calls()))

    def test_wallpaper_managed_session_uses_persistent_daemon_service(self):
        self.env.update(MOCK_UWSM='1', MOCK_GRAPHICAL='active')
        r = self.run_script('Wallpaper.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.calls()
        self.assertIn(['systemctl', '--user', 'start', 'hyprixe-awww.service'], calls)
        self.assertFalse(any(c[0] == 'awww-daemon' for c in calls))
        self.assertTrue(any(c[:2] == ['awww', 'img'] for c in calls))

    def test_early_hotplug_waits_for_session_unit_without_starting_a_daemon(self):
        self.env.update(MOCK_UWSM='1', MOCK_GRAPHICAL='inactive')
        r = self.run_script('Wallpaper.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('deferred', r.stdout)
        self.assertFalse(any(c[0] in ('awww', 'awww-daemon') or 'start' in c for c in self.calls()))

    def test_gui_launchers_use_uwsm_scopes_and_preserve_arguments(self):
        cases = [('LaunchApp.sh', ['dolphin', '/folder with spaces'], ['dolphin', '/folder with spaces']),
                 ('LaunchTerminal.sh', ['--directory', '/folder with spaces'],
                  ['kitty', '--directory', '/folder with spaces']),
                 ('RofiLauncher.sh', [], ['rofi', '-hyprixe-launcher', '-config',
                                         str(source_path(ROOT, '.config/hypr/rofi/config-launcher.rasi')), '-show', 'drun'])]
        for name, args, expected in cases:
            with self.subTest(name=name):
                (self.root / 'calls').write_text('')
                r = self.run_script(name, *args)
                self.assertEqual(r.returncode, 0, r.stderr)
                prefix = ['uwsm', 'app', '-t', 'scope', '--'] if name == 'RofiLauncher.sh' else ['uwsm', 'app', '--']
                self.assertIn([*prefix, *expected], self.calls())

    def test_launcher_sidebar_delegates_files_and_terminal_to_existing_uwsm_helpers(self):
        for status, command in ((10, 'dolphin'), (12, 'kitty')):
            with self.subTest(status=status):
                (self.root / 'calls').write_text('')
                self.env['MOCK_LAUNCHER_STATUS'] = str(status)
                result = self.run_script('RofiLauncher.sh')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.calls()[-1], ['uwsm', 'app', '--', command])
                self.assertEqual(sum('-hyprixe-launcher' in c for c in self.calls()), 1)

    def test_launcher_sidebar_windows_reuses_switcher_snapshot_and_dispatch(self):
        self.env['MOCK_LAUNCHER_STATUS'] = '11'
        result = self.run_script('RofiLauncher.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertEqual(sum(c[:2] == ['hyprctl', 'clients'] for c in calls), 1)
        rofi = next(c for c in calls if c[0] == 'rofi')
        self.assertIn('-dmenu', rofi)
        self.assertIn(str(source_path(ROOT, '.config/hypr/rofi/config-windows.rasi')), rofi)
        self.assertTrue(any(c[:2] == ['hyprctl', 'dispatch'] for c in calls))

    def test_launcher_accept_cancel_and_errors_never_launch_sidebar_apps(self):
        for status, expected in ((0, 0), (1, 0), (17, 17), (127, 127)):
            with self.subTest(status=status):
                (self.root / 'calls').write_text('')
                self.env['MOCK_LAUNCHER_STATUS'] = str(status)
                result = self.run_script('RofiLauncher.sh')
                self.assertEqual(result.returncode, expected)
                self.assertEqual(len(self.calls()), 1)
                if expected:
                    self.assertIn('Rofi launcher failed', result.stderr)

    def test_launcher_sidebar_works_with_custom_xdg_paths_containing_spaces(self):
        settings = self.root / 'settings with spaces'
        shutil.copytree(source_path(ROOT, '.config/hypr'), settings / 'hypr')
        self.env.update(XDG_CONFIG_HOME=str(settings), MOCK_LAUNCHER_STATUS='12')
        result = self.run_script('RofiLauncher.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(settings / 'hypr/rofi/config-launcher.rasi'), self.calls()[0])
        self.assertEqual(self.calls()[-1], ['uwsm', 'app', '--', 'kitty'])

    def test_power_menu_only_forwards_to_shared_wlogout_helper(self):
        helper = self.root / 'bin/hyprixe-session'
        helper.write_text(MOCK + '\nsys.exit(int(os.environ.get("MOCK_SESSION_STATUS", "0")))\n')
        helper.chmod(0o755)
        for status in (0, 17):
            with self.subTest(status=status):
                (self.root / 'calls').write_text('')
                self.env['MOCK_SESSION_STATUS'] = str(status)
                result = self.run_script('PowerMenu.sh')
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(self.calls(), [['hyprixe-session']])


class InstallPreflightTests(unittest.TestCase):
    PLATFORM = 'debian'
    def test_help_and_invalid_argument(self):
        r = subprocess.run(['bash', str(ROOT / 'install.sh'), '--help'], capture_output=True)
        self.assertEqual(r.returncode, 0)
        r = subprocess.run(['bash', str(ROOT / 'install.sh'), '--unknown'], capture_output=True)
        self.assertEqual(r.returncode, 2)

    def test_missing_dependencies_fail_with_nonzero_status(self):
        # Existing WSL/Linux test environment intentionally has no Hyprland session.
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PATH=tmp)
            r = subprocess.run(['/usr/bin/python3', str(source_path(ROOT, 'scripts/check-deps.py'))], env=env, capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn(b'Missing commands', r.stderr)

    @unittest.skipUnless(os.geteuid() == 0 and shutil.which('setpriv'), 'root/setpriv test harness required')
    def test_shell_dry_run_as_unprivileged_desktop_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chmod(tmp, 0o777)
            env = dict(os.environ, HOME=tmp, XDG_CONFIG_HOME=tmp+'/.config',
                       XDG_DATA_HOME=tmp+'/.local/share', XDG_STATE_HOME=tmp+'/.local/state')
            r = subprocess.run(['setpriv', '--reuid=65534', '--regid=65534', '--clear-groups',
                                'bash', str(ROOT / 'install.sh'), '--dry-run'], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('Profile native', r.stdout)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == '__main__': unittest.main()
