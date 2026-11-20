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


class PopupDismissalTests(unittest.TestCase):
    def setUp(self):
        self.window, self.scale, self.close, self.glib = (Mock() for _ in range(4))
        self.surface = Mock()
        self.surface.get_width.return_value = 244
        self.surface.get_height.return_value = 64
        self.window.get_window.return_value = self.surface
        self.gdk = SimpleNamespace(EventMask=SimpleNamespace(ENTER_NOTIFY_MASK=1, LEAVE_NOTIFY_MASK=2),
                                   CrossingMode=SimpleNamespace(NORMAL=0), NotifyType=SimpleNamespace(INFERIOR=2),
                                   BUTTON_PRIMARY=1, KEY_Escape=65307)
        self.glib.timeout_add.side_effect = (21, 22)
        self.glib.idle_add.return_value = 31
        self.dismiss = popup.PopupDismissal(self.window, self.scale, self.close, self.gdk, self.glib)
        self.crossing = SimpleNamespace(window=self.surface, mode=0, detail=0, x=50, y=30)

    def enter(self):
        self.dismiss.pointer_enter(self.window, self.crossing)

    def leave(self):
        self.dismiss.pointer_leave(self.window, self.crossing)

    def emit_focus(self, signal):
        for name, callback in (call.args for call in self.window.connect.call_args_list):
            if name == signal:
                callback(self.window, SimpleNamespace(window=self.surface))
        # Run an idle handler if the implementation defers focus handling.
        if self.glib.idle_add.called:
            self.glib.idle_add.call_args.args[0]()
            self.glib.idle_add.reset_mock()

    def test_leave_after_actual_enter_starts_one_three_second_timer(self):
        # A map event or a bogus outside enter must not start a countdown.
        outside = SimpleNamespace(**{**vars(self.crossing), 'y': -5})
        self.dismiss.pointer_enter(self.window, outside)
        self.leave()
        self.assertFalse(self.dismiss.pointer_has_entered)
        self.glib.timeout_add.assert_not_called()
        self.enter()
        self.assertTrue(self.dismiss.pointer_has_entered)
        self.leave()
        self.leave()
        self.glib.timeout_add.assert_called_once_with(3000, self.dismiss.expire)
        self.assertEqual(self.dismiss.close_timer, 21)
        self.close.assert_not_called()

    def test_reentry_cancels_and_next_leave_starts_a_new_timer(self):
        self.enter()
        self.leave()
        self.enter()
        self.glib.source_remove.assert_called_once_with(21)
        self.assertEqual(self.dismiss.close_timer, 0)
        self.leave()
        self.leave()
        self.assertEqual(self.dismiss.close_timer, 22)
        self.assertEqual(self.glib.timeout_add.call_count, 2)

    def test_timer_expiration_closes_once_without_removing_the_running_source(self):
        self.enter()
        self.leave()
        callback = self.glib.timeout_add.call_args.args[1]
        self.assertFalse(callback())
        self.assertEqual(self.dismiss.close_timer, 0)
        self.glib.source_remove.assert_not_called()
        self.dismiss.close()
        self.close.assert_called_once_with()

    def test_escape_cancels_the_timer_and_closes(self):
        self.enter()
        self.leave()
        self.assertFalse(self.dismiss.key_pressed(self.window, SimpleNamespace(keyval=0)))
        self.close.assert_not_called()
        self.assertTrue(self.dismiss.key_pressed(self.window, SimpleNamespace(keyval=self.gdk.KEY_Escape)))
        self.glib.source_remove.assert_called_once_with(21)
        self.close.assert_called_once_with()

    def test_toggle_closes_even_with_a_timer_and_cannot_restart_it(self):
        self.enter()
        self.leave()
        self.dismiss.close()  # Gtk.Application activation uses the same close path.
        self.enter()
        self.leave()
        self.glib.source_remove.assert_called_once_with(21)
        self.glib.timeout_add.assert_called_once()
        self.close.assert_called_once_with()

    def test_waybar_to_popup_survives_focus_loss_before_first_pointer_enter(self):
        self.emit_focus('focus-in-event')
        self.leave()
        self.emit_focus('focus-out-event')  # Pointer moved across the gap without a click.
        self.close.assert_not_called()
        self.assertFalse(self.dismiss.pointer_has_entered)
        self.glib.timeout_add.assert_not_called()
        self.enter()
        self.assertTrue(self.dismiss.pointer_has_entered)
        self.assertTrue(self.dismiss.pointer_inside)
        self.close.assert_not_called()

    def test_focus_follows_mouse_leave_keeps_the_pending_timer(self):
        self.emit_focus('focus-in-event')
        self.enter()
        self.leave()
        self.emit_focus('focus-out-event')
        self.close.assert_not_called()
        self.glib.source_remove.assert_not_called()
        self.assertEqual(self.dismiss.close_timer, 21)
        self.enter()
        self.glib.source_remove.assert_called_once_with(21)
        self.close.assert_not_called()

    def test_focus_changes_inside_popup_do_not_close_or_arm(self):
        self.emit_focus('focus-in-event')
        self.enter()
        self.emit_focus('focus-out-event')
        self.glib.timeout_add.assert_not_called()
        self.close.assert_not_called()

    def test_drag_outside_suspends_dismissal_until_release(self):
        self.dismiss.drag_start(self.scale, SimpleNamespace(button=1))
        self.leave()
        self.emit_focus('focus-out-event')
        self.glib.timeout_add.assert_not_called()
        self.close.assert_not_called()
        scale_window = Mock()
        scale_window.get_parent.return_value = self.surface
        scale_window.coords_to_parent.side_effect = lambda x, y: (x + 15, y + 44)
        self.dismiss.drag_end(self.scale, SimpleNamespace(button=1, window=scale_window, x=60, y=27))
        self.assertFalse(self.dismiss.drag_active)
        self.glib.timeout_add.assert_called_once_with(3000, self.dismiss.expire)

    def test_release_inside_does_not_start_a_timer(self):
        self.dismiss.drag_start(self.scale, SimpleNamespace(button=1))
        self.leave()
        self.dismiss.drag_end(self.scale, SimpleNamespace(button=1, window=self.surface, x=60, y=55))
        self.assertTrue(self.dismiss.pointer_inside)
        self.glib.timeout_add.assert_not_called()

    def test_child_and_synthetic_crossings_do_not_count_as_leaving(self):
        self.enter()
        for changes in ({'detail': self.gdk.NotifyType.INFERIOR}, {'window': Mock()}, {'mode': 1}):
            self.dismiss.pointer_leave(self.window, SimpleNamespace(**{**vars(self.crossing), **changes}))
        self.assertTrue(self.dismiss.pointer_inside)
        self.glib.timeout_add.assert_not_called()

    def test_hidden_or_destroyed_window_cancels_pending_timer(self):
        self.enter()
        self.leave()
        self.dismiss.stop()
        self.dismiss.stop()
        self.glib.source_remove.assert_called_once_with(21)
        self.close.assert_not_called()
