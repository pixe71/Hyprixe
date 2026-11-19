"""Backlight, logind and popup contracts without a display or device."""

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'common/local/bin/hyprixe-brightness-popup'
loader = importlib.machinery.SourceFileLoader('brightness_popup', str(HELPER))
spec = importlib.util.spec_from_loader(loader.name, loader)
popup = importlib.util.module_from_spec(spec)
loader.exec_module(popup)


class BrightnessPopupTests(unittest.TestCase):
    def test_selects_highest_maximum_and_breaks_ties_by_sysfs_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backlight = root / 'class'
            backlight.mkdir()
            for name, location, maximum in (('first-link', 'z-device', 937), ('last-link', 'a-device', 937),
                                            ('lower', 'b-device', 100), ('invalid', 'bad', 0)):
                device = root / location
                device.mkdir()
                (device / 'max_brightness').write_text(str(maximum))
                (backlight / name).symlink_to(device)
            selected = popup.select_backlight(backlight)
            self.assertEqual((selected.name, selected.maximum), ('last-link', 937))

    def test_read_uses_actual_or_driver_requested_level(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('generic-backlight', 'amdgpu_bl42', 'apple-panel-bl'):
                path = Path(folder) / name
                path.mkdir()
                (path / 'brightness').write_text('75')
                (path / 'actual_brightness').write_text('67')
                device = popup.Backlight(path, 100)
                self.assertEqual(device.level(), 67 if name == 'generic-backlight' else 75)
                (path / 'actual_brightness').unlink()
                self.assertEqual(device.level(), 75)

    def test_rounds_up_to_first_safe_hardware_step(self):
        for maximum, minimum in ((1, 1), (7, 1), (100, 5), (255, 13), (937, 47)):
            with self.subTest(maximum=maximum):
                self.assertEqual(popup.hardware_value(5, maximum), minimum)
                self.assertEqual(popup.hardware_value(0, maximum), minimum)
                self.assertEqual(popup.hardware_value(100, maximum), maximum)
                for percent in range(5, 101):
                    level = popup.hardware_value(percent, maximum)
                    self.assertGreaterEqual(level * 100, 5 * maximum)
                    self.assertLessEqual(level, maximum)
        self.assertEqual(popup.display_percent(171, 255), 67)
        self.assertEqual(popup.display_percent(0, 100), 0)

    def test_no_backlight_exits_before_runtime_or_gtk(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(popup.select_backlight(Path(folder)))
        with patch.object(popup, 'select_backlight', return_value=None), \
                patch.object(popup, 'runtime_directory') as runtime, patch.object(popup, 'message') as message:
            self.assertEqual(popup.main(['--toggle']), 0)
            runtime.assert_not_called()
            message.assert_called_once_with('Aucun périphérique de rétroéclairage.')

    def test_logind_arguments_auto_self_fallback_and_permission_denial(self):
        connection = Mock()
        gio = Mock()
        gio.DBusError.get_remote_error.side_effect = str
        glib = SimpleNamespace(Error=ValueError, Variant=lambda *args: args)
        errors = ('org.freedesktop.login1.NoSessionForPID', 'org.freedesktop.DBus.Error.AccessDenied')
        for remote_error in errors:
            with self.subTest(error=remote_error):
                connection.reset_mock()
                logind = popup.Logind(connection, gio, glib)
                done = Mock()
                logind.set_brightness('panel', 13, done)
                args = connection.call.call_args.args
                self.assertEqual(args[:5], ('org.freedesktop.login1', popup.SESSION_PATH + 'auto',
                                            'org.freedesktop.login1.Session', 'SetBrightness',
                                            ('(ssu)', ('backlight', 'panel', 13))))
                failure = ValueError(remote_error)
                connection.call_finish.side_effect = failure
                args[-2](connection, 'result', args[-1])
                if remote_error.endswith('AccessDenied'):
                    self.assertEqual(connection.call.call_count, 1)
                    done.assert_called_once_with(failure)
                else:
                    retry = connection.call.call_args.args
                    self.assertEqual(retry[1], popup.SESSION_PATH + 'self')
                    self.assertEqual(retry[4], args[4])
                    done.assert_not_called()
                    connection.call_finish.side_effect = None
                    retry[-2](connection, 'result', retry[-1])
                    done.assert_called_once_with(None)

    def test_live_updates_coalesce_poll_and_flush_last_change_on_close(self):
        window, scale, label, logind, glib = (Mock() for _ in range(5))
        glib.timeout_add.side_effect = (1, 2, 3)
        device = SimpleNamespace(maximum=255, name='panel', level=Mock())
        device.level.return_value = 171
        slider = popup.BrightnessSlider(window, scale, label, device, logind, glib)
        scale.set_value.assert_called_once_with(67)
        label.set_text.assert_called_once_with('67 %')
        logind.set_brightness.assert_not_called()

        device.level.return_value = 191
        self.assertTrue(slider.refresh())
        scale.set_value.assert_called_with(75)
        scale.handler_block.assert_called_once_with(slider.handler)
        for percent in (55, 52, 51):
            scale.get_value.return_value = percent
            slider.changed(scale)
        self.assertEqual(glib.timeout_add.call_count, 2)
        self.assertFalse(slider.write())
        logind.set_brightness.assert_called_once_with('panel', 130, slider.finished)
        scale.get_value.return_value = 5
        slider.changed(scale)
        slider.close()
        window.hide.assert_called_once()
        window.destroy.assert_not_called()
        slider.finished(None)
        self.assertEqual(glib.timeout_add.call_count, 3)
        self.assertFalse(slider.write())
        logind.set_brightness.assert_called_with('panel', 13, slider.finished)
        slider.finished(None)
        window.destroy.assert_called_once()

    def test_runtime_directory_and_single_instance_session_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runtime = root / 'private runtime'
            runtime.mkdir(mode=0o700)
            env = {'XDG_RUNTIME_DIR': str(runtime), 'WAYLAND_DISPLAY': 'wayland-1'}
            self.assertEqual(popup.runtime_directory(env), runtime)
            self.assertRegex(popup.application_id(env), r'^org\.hyprixe\.BrightnessPopup\.Session[0-9a-f]{16}$')
            self.assertEqual(popup.application_id(env), popup.application_id(dict(env)))
            self.assertNotEqual(popup.application_id(env), popup.application_id(dict(env, WAYLAND_DISPLAY='wayland-2')))
            self.assertNotEqual(popup.application_id(env), popup.application_id(dict(env, HYPRLAND_INSTANCE_SIGNATURE='other')))
            link = root / 'link'
            link.symlink_to(runtime)
            with self.assertRaises(ValueError):
                popup.runtime_directory(dict(env, XDG_RUNTIME_DIR=str(link)))
            with self.assertRaises(ValueError):
                popup.runtime_directory(dict(env, XDG_RUNTIME_DIR='relative'))
            with patch.object(os, 'getuid', return_value=runtime.stat().st_uid + 1), self.assertRaises(ValueError):
                popup.runtime_directory(env)
            runtime.chmod(0o755)
            with self.assertRaises(ValueError):
                popup.runtime_directory(env)

    def test_monitor_uses_compositor_coordinates_and_falls_back(self):
        monitors = [Mock(), Mock()]
        monitors[0].get_geometry.return_value = SimpleNamespace(x=-1200, y=150, width=1200, height=700)
        monitors[1].get_geometry.return_value = SimpleNamespace(x=0, y=0, width=1920, height=1080)
        display = Mock()
        display.get_n_monitors.return_value = 2
        display.get_monitor.side_effect = lambda index: monitors[index]
        env = {'HYPRLAND_INSTANCE_SIGNATURE': 'session'}
        with patch.object(subprocess, 'run') as run:
            self.assertIsNone(popup.monitor_at_pointer(display, {}))
            run.assert_not_called()
            for point, expected in (({'x': -101.2, 'y': 200}, monitors[0]),
                                    ({'x': 0, 'y': 200}, monitors[1]),
                                    ({'x': -1, 'y': 0}, None)):
                run.return_value.stdout = json.dumps(point)
                self.assertIs(popup.monitor_at_pointer(display, env), expected)
            run.assert_called_with(['hyprctl', '-j', 'cursorpos'], capture_output=True,
                                   text=True, timeout=0.5, check=True, env=env)
            run.side_effect = subprocess.TimeoutExpired('hyprctl', 0.5)
            self.assertIsNone(popup.monitor_at_pointer(display, env))

    def test_dynamic_colours_and_safe_frosted_glass_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            env = {'XDG_CACHE_HOME': str(home / 'cache with spaces')}
            path = Path(env['XDG_CACHE_HOME']) / 'hyprixe/theme/current/palette.json'
            path.parent.mkdir(parents=True)
            colours = dict(popup.DEFAULT_COLOURS, accent='#aaccee')
            path.write_text(json.dumps(colours))
            css = popup.popup_css(popup.popup_colours(env, home)).decode()
            self.assertIn('scale highlight { background-color: #aaccee; }', css)
            self.assertIn('scale slider {', css)
            self.assertIn('background-color: alpha(#122434, 0.88)', css)
            path.write_text(json.dumps(dict(colours, accent='invalid CSS')))
            self.assertEqual(popup.popup_colours(env, home), popup.DEFAULT_COLOURS)
        default = ROOT / 'common/theme/defaults/frosted-glass.json'
        original = json.loads(default.read_text())
        self.assertEqual(popup.DEFAULT_COLOURS, {role: original[role] for role in popup.DEFAULT_COLOURS})

    def test_debian_runtime_dependencies_and_helper_shebang(self):
        path = ROOT / 'profiles/debian/packages/packages.txt'
        packages = {line.split('#')[0].strip() for line in path.read_text().splitlines()}
        self.assertLessEqual({'python3-gi', 'gir1.2-gtk-3.0', 'gir1.2-gtklayershell-0.1'}, packages)
        self.assertTrue(HELPER.read_text().startswith('#!/usr/bin/env python3\n'))
