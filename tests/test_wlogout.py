import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import deploy
import wlogout_checks as checks

loader = importlib.machinery.SourceFileLoader('hyprixe_session', str(ROOT / '.local/bin/hyprixe-session'))
spec = importlib.util.spec_from_loader(loader.name, loader)
session = importlib.util.module_from_spec(spec)
loader.exec_module(session)


class SessionMenuTests(unittest.TestCase):
    def test_logical_geometry_is_centered_scaled_and_rotated(self):
        for width, height, scale, transform in ((1920, 1080, 1, 0), (2560, 1440, 2, 0),
                                                (1366, 768, 1, 0), (3840, 2160, 1.5, 0),
                                                (1920, 1080, 1, 1), (1080, 1920, 1, 3)):
            with self.subTest(width=width, height=height, scale=scale, transform=transform):
                monitors = [dict(width=width, height=height, scale=scale, focused=True, transform=transform)]
                left, top = session.margins(monitors)
                if transform % 2:
                    width, height = height, width
                self.assertAlmostEqual((width / scale - 2 * left) / (width / scale), .70, delta=.002)
                self.assertAlmostEqual((height / scale - 2 * top) / (height / scale), .26, delta=.002)

    def test_invalid_or_missing_output_is_refused(self):
        for monitors in ({}, [], [None], [dict(focused=False)],
                         [dict(focused=True, width=1920, height=1080, scale=0)],
                         [dict(focused=True, width=1920, height=1080, scale=float('nan'))]):
            with self.subTest(monitors=monitors), self.assertRaises(ValueError):
                session.margins(monitors)

    def test_lock_reuses_the_existing_duplicate_guard_without_confirmation(self):
        with patch.object(session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(session.action('lock', Path('/custom settings')), 0)
        self.assertEqual(run.call_args.args[0], ['/custom settings/hypr/scripts/LockScreen.sh'])
        self.assertEqual(run.call_count, 1)

    def test_cancel_escape_unexpected_answer_or_rofi_error_never_dispatch(self):
        for name in ('logout', 'shutdown', 'reboot'):
            for output, status in (('Cancel\n', 0), ('Confirm something else', 0), ('', 1), ('Confirm\n', 17)):
                with self.subTest(name=name, output=output, status=status):
                    calls = []
                    def run(args, **kwargs):
                        calls.append(args)
                        if args[0] == 'uwsm':
                            return subprocess.CompletedProcess(args, 0)
                        self.assertEqual(args[0], 'rofi')
                        self.assertEqual(kwargs['input'], 'Cancel\nConfirm\n')
                        self.assertIn('-selected-row', args)
                        return subprocess.CompletedProcess(args, status, output, 'fixture error')
                    with patch.object(session.subprocess, 'run', side_effect=run):
                        if status == 17:
                            with self.assertRaises(ValueError):
                                session.action(name, Path('/config'))
                        else:
                            self.assertEqual(session.action(name, Path('/config')), 0)
                    self.assertFalse(any(args[0] == 'systemctl' or args[:2] == ['uwsm', 'stop'] for args in calls))

    def test_only_confirmed_fixed_action_is_dispatched_and_failure_propagates(self):
        for name, expected in (('logout', ['uwsm', 'stop']), ('shutdown', ['systemctl', 'poweroff']),
                               ('reboot', ['systemctl', 'reboot'])):
            with self.subTest(name=name):
                replies = ([subprocess.CompletedProcess([], 0)] if name == 'logout' else [])
                replies += [subprocess.CompletedProcess([], 0, 'Confirm\n', ''), subprocess.CompletedProcess([], 19)]
                with patch.object(session.subprocess, 'run', side_effect=replies) as run:
                    self.assertEqual(session.action(name, Path('/config')), 19)
                self.assertEqual(run.call_args.args[0], expected)

    def test_logout_refuses_an_unmanaged_session(self):
        with patch.object(session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)) as run:
            with self.assertRaisesRegex(ValueError, 'uwsm-managed'):
                session.action('logout', Path('/config'))
        self.assertEqual(run.call_count, 1)

    def test_unknown_actions_are_rejected_by_cli(self):
        for name in ('suspend', 'hibernate', 'poweroff;anything'):
            result = subprocess.run(['python3', str(ROOT / '.local/bin/hyprixe-session'), name], capture_output=True)
            self.assertEqual(result.returncode, 2)

    def test_toggle_stops_only_our_active_or_starting_menu(self):
        with tempfile.TemporaryDirectory() as runtime, patch.dict(os.environ, XDG_RUNTIME_DIR=runtime):
            for state in ('active', 'activating'):
                with self.subTest(state=state), patch.object(session.subprocess, 'run', side_effect=[
                        subprocess.CompletedProcess([], 0, state + '\n', ''), subprocess.CompletedProcess([], 0)]) as run:
                    self.assertEqual(session.menu(Path('/custom settings')), 0)
                    self.assertEqual(run.call_args.args[0], ['systemctl', '--user', 'stop', 'hyprixe-wlogout.service'])
                    self.assertEqual(run.call_count, 2)

    def test_launch_is_one_named_uwsm_service_with_four_columns_and_custom_xdg(self):
        monitors = [dict(width=1920, height=1080, scale=1, focused=True)]
        replies = [subprocess.CompletedProcess([], 1, '', ''), subprocess.CompletedProcess([], 0),
                   subprocess.CompletedProcess([], 0, json.dumps(monitors), ''), subprocess.CompletedProcess([], 0)]
        with tempfile.TemporaryDirectory() as runtime, patch.dict(os.environ, XDG_RUNTIME_DIR=runtime), \
             patch.object(session.subprocess, 'run', side_effect=replies) as run:
            self.assertEqual(session.menu(Path('/custom settings')), 0)
        args = run.call_args.args[0]
        self.assertEqual(args[:10], ['uwsm', 'app', '-s', 'a', '-t', 'service', '-u', 'hyprixe-wlogout.service', '--', 'wlogout'])
        for key, value in (('--buttons-per-row', '4'), ('--layout', '/custom settings/wlogout/layout'),
                           ('--css', '/custom settings/wlogout/style.css'), ('--margin-left', '288'), ('--margin-top', '400')):
            self.assertEqual(args[args.index(key) + 1], value)
        self.assertIn('--no-span', args)


class WlogoutDeploymentTests(unittest.TestCase):
    def test_debian_svg_loader_filename_is_detected_and_missing_loader_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp)
            loader = library / 'architecture/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader_svg.so'
            loader.parent.mkdir(parents=True)
            loader.touch()
            with patch.object(checks, 'Path', return_value=library), \
                 patch.object(checks.shutil, 'which', return_value='/usr/bin/wlogout'):
                self.assertEqual(checks.runtime_errors(), [])
                loader.unlink()
                self.assertEqual(checks.runtime_errors(), ['Wlogout SVG icon loader missing; install librsvg2-common'])

    def test_full_install_repeat_restore_preserves_previous_menu_and_other_apps(self):
        with tempfile.TemporaryDirectory(prefix='hyprixe wlogout ') as tmp:
            home = Path(tmp)
            roots = {key: home / name for key, name in (('config', 'settings with spaces'), ('data', 'data'), ('state', 'state'))}
            before = {
                roots['config'] / 'wlogout/layout': b'old personal layout',
                roots['config'] / 'wlogout/style.css': b'old personal style',
                home / '.local/bin/hyprixe-session': b'old personal helper',
                roots['config'] / 'hypr/lua/keybinds.lua': b'old binds',
                roots['config'] / 'hypr/lua/rules.lua': b'old rules',
                roots['config'] / 'hypr/scripts/PowerMenu.sh': b'old personal power menu',
            }
            for path, data in before.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            # Fixtures inherit the caller's umask; restore must keep their actual original modes.
            before_modes = {path: path.stat().st_mode & 0o777 for path in before}
            personal = roots['config'] / 'wlogout/personal-notes'
            personal.write_text('keep me')
            with patch.dict(os.environ, HOME=str(home)), contextlib.redirect_stdout(io.StringIO()):
                deploy.install(home, roots, 'native')
                backups = list((roots['state'] / 'hyprixe/backups').iterdir())
                self.assertEqual(len(backups), 1)
                checks.validate(roots['config'])
                helper = home / '.local/bin/hyprixe-session'
                self.assertEqual(helper.stat().st_mode & 0o777, 0o755)
                self.assertEqual(helper.read_bytes(), (ROOT / '.local/bin/hyprixe-session').read_bytes())
                bridge = roots['config'] / 'hypr/scripts/PowerMenu.sh'
                self.assertEqual(bridge.stat().st_mode & 0o777, 0o755)
                self.assertEqual(bridge.read_bytes(), (ROOT / '.config/hypr/scripts/PowerMenu.sh').read_bytes())
                self.assertEqual((roots['config'] / 'hypr/scripts/RofiLauncher.sh').read_bytes(),
                                 (ROOT / '.config/hypr/scripts/RofiLauncher.sh').read_bytes())
                deploy.install(home, roots, 'native')
                self.assertEqual(list((roots['state'] / 'hyprixe/backups').iterdir()), backups)
                deploy.restore(backups[0], home)
            for path, data in before.items():
                self.assertEqual(path.read_bytes(), data)
                self.assertEqual(path.stat().st_mode & 0o777, before_modes[path])
            self.assertEqual(personal.read_text(), 'keep me')
            self.assertFalse((roots['config'] / 'wlogout/icons/lock.svg').exists())

    def test_layout_stream_and_invalid_duplicate_or_extra_actions(self):
        checks.validate(ROOT / '.config')
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp)
            shutil.copytree(ROOT / '.config/wlogout', config / 'wlogout')
            layout = config / 'wlogout/layout'
            original = layout.read_text()
            for text in ('[]', original + original, original.replace('"reboot"', '"suspend"'), 'invalid'):
                with self.subTest(text=text[:30]):
                    layout.write_text(text)
                    with self.assertRaises(ValueError):
                        checks.validate(config)
            layout.write_text(original)
            (config / 'wlogout/icons/lock.svg').unlink()
            with self.assertRaises(OSError):
                checks.validate(config)

    def test_missing_files_are_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = []
            checks.check_source(lambda ok, msg: results.append((ok, msg)), tmp)
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0][0])

    def test_legacy_menu_shortcuts_or_bridge_and_changed_launcher_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            for relative in ('.config/wlogout', '.config/hypr'):
                shutil.copytree(ROOT / relative, source / relative)
            helper = source / '.local/bin/hyprixe-session'
            helper.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / '.local/bin/hyprixe-session', helper)
            binds = source / '.config/hypr/lua/keybinds.lua'
            bridge = source / '.config/hypr/scripts/PowerMenu.sh'
            original = binds.read_text()
            variants = [('', original)]
            for chord in ('SUPER + Backspace', 'SUPER + SHIFT + E'):
                target = 'bind("' + chord + '", d.exec_cmd("hyprixe-session")'
                variants += [(chord, original.replace(target, 'bind("' + chord + '", script("PowerMenu.sh")')),
                             ('duplicate ' + chord, original + '\n' + target + ')\n')]
            variants.append(('launcher', original.replace('script("RofiLauncher.sh")', 'script("PowerMenu.sh")')))
            for damage, text in variants:
                with self.subTest(damage=damage):
                    binds.write_text(text)
                    results = []
                    with patch.object(checks, 'check_css'), contextlib.redirect_stdout(io.StringIO()):
                        checks.check_source(lambda ok, msg: results.append((ok, msg)), source)
                    self.assertEqual(all(ok for ok, _ in results), not damage, results)
            binds.write_text(original)
            bridge.write_text('#!/usr/bin/env bash\nrofi -dmenu -p Session\n')
            results = []
            checks.check_source(lambda ok, msg: results.append((ok, msg)), source)
            self.assertFalse(results[0][0])
            self.assertIn('only forward', results[0][1])

    def test_missing_required_asset_aborts_deployment_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'repository'
            shutil.copytree(ROOT / '.config', source / '.config')
            (source / '.config/wlogout/style.css').unlink()
            home = Path(tmp) / 'home'
            home.mkdir()
            roots = {key: home / key for key in ('config', 'data', 'state')}
            with patch.dict(os.environ, HOME=str(home)), patch.object(deploy, 'REPO', source):
                with self.assertRaises(OSError):
                    deploy.install(home, roots, 'native')
            self.assertEqual(list(home.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
