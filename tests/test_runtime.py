import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.config/hypr/scripts'
MOCK = '''#!/usr/bin/python3
import json, os, pathlib, sys
name=pathlib.Path(sys.argv[0]).name
root=pathlib.Path(os.environ['MOCK_ROOT'])
with (root/'calls').open('a') as f: f.write(json.dumps([name]+sys.argv[1:])+'\\n')
if name=='hyprctl':
    if sys.argv[1]=='monitors': print('[{"name":"DP-3"},{"name":"eDP-2"}]')
    elif sys.argv[1]=='clients':
        print('[{"mapped":true,"address":"0xabc","class":"Alacritty","title":"Example"}]')
elif name=='awww' and sys.argv[1]=='query':
    if os.environ.get('MOCK_NEVER_READY') or not (root/'ready').exists(): sys.exit(1)
    print('DP-3: 2560x1440, scale: 1, currently displaying: image\\neDP-2: 1920x1080')
elif name=='awww-daemon': (root/'ready').touch()
elif name=='rofi':
    if os.environ.get('MOCK_CANCEL'): sys.exit(1)
    print(os.environ.get('MOCK_INDEX','0'))
elif name=='systemctl':
    if 'is-enabled' in sys.argv or 'is-active' in sys.argv:
        sys.exit(0 if os.environ.get('MOCK_SERVICE')=='enabled' else 1)
elif name=='pgrep': sys.exit(1)
'''


@unittest.skipUnless(shutil.which('jq'), 'jq required for runtime script mocks')
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-runtime-test-')
        self.root = Path(self.temp.name)
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        for name in ('hyprctl', 'awww', 'awww-daemon', 'rofi', 'sleep', 'systemctl', 'pgrep', 'waybar'):
            p = bin_dir / name
            p.write_text(MOCK)
            p.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.root), XDG_RUNTIME_DIR=str(self.root),
                        XDG_CONFIG_HOME=str(ROOT / '.config'), XDG_DATA_HOME=str(self.root / 'data'),
                        XDG_STATE_HOME=str(self.root / 'state'), MOCK_ROOT=str(self.root),
                        PATH=str(bin_dir) + ':' + os.environ['PATH'])
        wallpaper = self.root / 'data/hyprixe/wallpapers/min_forest.jpg'
        wallpaper.parent.mkdir(parents=True)
        wallpaper.write_bytes(b'wallpaper fixture')

    def tearDown(self): self.temp.cleanup()

    def run_script(self, name):
        return subprocess.run(['bash', str(SCRIPTS / name)], env=self.env, capture_output=True, text=True, timeout=15)

    def calls(self):
        return [json.loads(line) for line in (self.root / 'calls').read_text().splitlines()]

    def test_wallpaper_reuses_daemon_and_applies_to_all_outputs(self):
        (self.root / 'ready').touch()
        r = self.run_script('Wallpaper.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.calls()
        self.assertFalse(any(c[0] == 'awww-daemon' for c in calls))
        img = next(c for c in calls if c[:2] == ['awww', 'img'])
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

    def test_switcher_invalid_index_fails_without_dispatch(self):
        self.env['MOCK_INDEX'] = '999'
        self.assertNotEqual(self.run_script('WindowSwitcher.sh').returncode, 0)
        self.assertFalse(any(c[:2] == ['hyprctl', 'dispatch'] for c in self.calls()))

    def test_waybar_reuses_enabled_service(self):
        self.env['MOCK_SERVICE'] = 'enabled'
        r = self.run_script('WaybarStartup.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.calls()
        self.assertTrue(any(c[:3] == ['systemctl', '--user', 'start'] for c in calls))
        self.assertFalse(any(c[0] == 'waybar' for c in calls))

    def test_waybar_direct_launch_uses_explicit_config_and_style(self):
        r = self.run_script('WaybarStartup.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        call = next(c for c in self.calls() if c[0] == 'waybar')
        self.assertEqual(call[1:], ['-c', str(ROOT / '.config/hypr/waybar/config'), '-s', str(ROOT / '.config/hypr/waybar/style.css')])


class InstallPreflightTests(unittest.TestCase):
    def test_help_and_invalid_argument(self):
        r = subprocess.run(['bash', str(ROOT / 'install.sh'), '--help'], capture_output=True)
        self.assertEqual(r.returncode, 0)
        r = subprocess.run(['bash', str(ROOT / 'install.sh'), '--unknown'], capture_output=True)
        self.assertEqual(r.returncode, 2)

    def test_missing_dependencies_fail_with_nonzero_status(self):
        # Existing WSL/Linux test environment intentionally has no Hyprland session.
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PATH=tmp)
            r = subprocess.run(['/usr/bin/python3', str(ROOT / 'scripts/check-deps.py')], env=env, capture_output=True)
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
