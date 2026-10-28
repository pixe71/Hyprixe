"""Registry schema/IPC regressions; fixtures are not physical input tests."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from keybind_checks import (API_PROBE, EXPECTED, PREFIX,
                            check_native_config, check_session_keybinds, handle_probe, registry_errors)


def registry():
    # Lua JSON in both audited versions: code:N is omitted, mouse=false,
    # dispatcher=__lua, arg=registry reference; enabled is NOT exported.
    return [dict(description=PREFIX + spec.chord, key='' if spec.key.startswith('code:') else spec.key,
                 keycode=0, modmask=spec.mask, submap='', dispatcher='__lua', arg=str(i + 1),
                 locked=spec.locked, release=False, mouse=False, non_consuming=False,
                 longPress=False, catch_all=False, **{'repeat': spec.repeating})
            for i, spec in enumerate(EXPECTED)]


class RegistryTests(unittest.TestCase):
    def test_complete_native_registry_and_physical_workspace_codes(self):
        self.assertEqual(len(EXPECTED), 68)
        self.assertEqual(len({b.chord for b in EXPECTED}), 68)
        self.assertEqual(registry_errors(registry()), [])

    def test_missing_alt_tab_and_legacy_descriptions_fail(self):
        rows = registry()
        rows = [r for r in rows if r['description'] != PREFIX + 'ALT + Tab']
        errors = registry_errors(rows)
        self.assertTrue(any('ALT + Tab: expected one' in x for x in errors))
        self.assertTrue(any('expected one' in x for x in registry_errors([dict(r, description='old') for r in rows])))

    def test_duplicate_chord_from_personal_override_is_detected(self):
        rows = registry()
        rows.append(dict(next(r for r in rows if r['key'] == 'F10'), description='Personal override'))
        self.assertTrue(any('Duplicate/conflicting' in x for x in registry_errors(rows)))

    def test_flags_modifiers_submap_key_and_removed_callback_are_checked(self):
        for field, value in (('modmask', 4), ('repeat', True), ('submap', 'resize'), ('mouse', True),
                             ('key', 'Escape'), ('arg', '-2'), ('release', True), ('non_consuming', True)):
            with self.subTest(field=field):
                rows = registry()
                rows[0][field] = value
                self.assertTrue(registry_errors(rows))

    def test_different_submap_or_release_is_not_a_duplicate(self):
        rows = registry()
        rows += [dict(rows[0], description='Release', release=True),
                 dict(rows[0], description='Other submap', submap='resize')]
        self.assertEqual(registry_errors(rows), [])

    def test_opaque_unlabelled_physical_bind_is_not_assumed_conflict_free(self):
        rows = registry() + [dict(registry()[0], description='', key='', keycode=0)]
        self.assertTrue(any('Opaque unlabelled' in x for x in registry_errors(rows)))

    def test_malformed_top_level_is_reported(self):
        for value in (None, {}, [None]):
            self.assertTrue(registry_errors(value))


class NativeParserTests(unittest.TestCase):
    def test_parser_uses_private_config_and_environment_and_does_not_start_a_session(self):
        results = []
        def runner(command, **kwargs):
            self.assertIn('--verify-config', command)
            config = Path(command[-1])
            self.assertNotEqual(config, ROOT / '.config/hypr/hyprland.lua')
            self.assertIn(handle_probe(), config.read_text())
            self.assertIn(API_PROBE, config.read_text())
            for name in ('HYPRLAND_INSTANCE_SIGNATURE', 'WAYLAND_DISPLAY', 'DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                self.assertNotIn(name, kwargs['env'])
            self.assertEqual(kwargs['env']['HOME'], str(config.parents[2]))
            self.assertEqual(Path(kwargs['env']['XDG_RUNTIME_DIR']).stat().st_mode & 0o777, 0o700)
            return subprocess.CompletedProcess(command, 0, 'config ok', '')
        with patch('keybind_checks.shutil.which', return_value='/usr/bin/Hyprland'), \
             patch('keybind_checks.os.geteuid', return_value=1000), \
             patch('keybind_checks.subprocess.run', side_effect=runner):
            check_native_config(lambda ok, msg: results.append((ok, msg)), ROOT)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][0])

    def test_parser_failure_is_reported(self):
        results = []
        with patch('keybind_checks.shutil.which', return_value='/usr/bin/Hyprland'), \
             patch('keybind_checks.os.geteuid', return_value=1000), \
             patch('keybind_checks.subprocess.run', return_value=subprocess.CompletedProcess([], 1, 'invalid API', '')), \
             contextlib.redirect_stdout(io.StringIO()):
            check_native_config(lambda ok, msg: results.append((ok, msg)), ROOT)
        self.assertFalse(results[0][0])


class SessionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe keybind checks ')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        shutil.copytree(ROOT / '.config/hypr', self.home / '.config/hypr')
        self.env = {'HOME': str(self.home), 'HYPRLAND_INSTANCE_SIGNATURE': 'fixture', 'WAYLAND_DISPLAY': 'fixture'}
        self.commands = []
        self.rows = registry()
        self.eval_result = 'ok'
        self.dispatch_result = 'ok'
        self.configerrors = ''
        self.submap = 'default'

    def runner(self, command, **kwargs):
        self.commands.append(command)
        output = 'ok'
        if command[1:] == ['version']: output = 'Hyprland 0.56.2 built from branch at commit fixture'
        elif command[1:] == ['configerrors']: output = self.configerrors
        elif command[1:] == ['-j', 'binds']: output = json.dumps(self.rows)
        elif command[1] == 'eval': output = self.eval_result
        elif command[1] == 'dispatch': output = self.dispatch_result
        elif command[1:] == ['submap']: output = self.submap
        elif command[1:] == ['-j', 'devices']:
            output = '{"keyboards":[{"name":"fixture","active_keymap":"French (legacy, alt.)"}]}'
        return subprocess.CompletedProcess(command, 0, output, '')

    def check(self, which=None, runner=None):
        results = []
        with patch('rofi_compat.has_wayland_support', return_value=True), contextlib.redirect_stdout(io.StringIO()):
            check_session_keybinds(lambda ok, msg: results.append((ok, msg)), ROOT,
                                  self.env, runner or self.runner, which or (lambda cmd: '/bin/' + cmd))
        return results

    def test_live_queries_and_handles_are_required_without_window_actions(self):
        result = self.check()
        self.assertTrue(all(ok for ok, _ in result), result)
        self.assertIn(['hyprctl', '-j', 'binds'], self.commands)
        evaluations = [c for c in self.commands if c[1] == 'eval']
        self.assertEqual(len(evaluations), 1)
        self.assertTrue(evaluations[0][2].startswith(handle_probe()))
        dispatches = [c for c in self.commands if c[1] == 'dispatch']
        self.assertEqual(dispatches, [['hyprctl', 'dispatch', API_PROBE]])
        self.assertIn('return d.no_op()', API_PROBE)
        self.assertNotIn('hl.dispatch', API_PROBE)

    def test_disabled_or_removed_handle_and_api_error_fail_even_on_zero_exit(self):
        self.eval_result = 'Lua error: Disabled/removed ALT + Tab'
        self.dispatch_result = 'Lua error: unsupported cycle_next'
        failures = [msg for ok, msg in self.check() if not ok]
        self.assertEqual(len(failures), 2, failures)
        self.assertIn('Disabled/removed', failures[0])

    def test_existing_configerrors_are_reported_before_lua_and_never_cleared(self):
        self.configerrors = 'Original load error'
        failures = [msg for ok, msg in self.check() if not ok]
        self.assertTrue(any('Original load error' in msg for msg in failures))
        self.assertFalse(any(c[1] in ('eval', 'dispatch') for c in self.commands))
        self.assertIn(['hyprctl', '-j', 'binds'], self.commands)

    def test_non_root_submap_and_missing_commands_report_failures(self):
        self.submap = 'resize'
        failures = [msg for ok, msg in self.check(which=lambda cmd: None if cmd == 'jq' else '/bin/' + cmd) if not ok]
        self.assertTrue(any('Current submap: resize' in x for x in failures))
        self.assertTrue(any('missing jq' in x for x in failures))

    def test_missing_or_non_executable_installed_script_and_drift(self):
        script = self.home / '.config/hypr/scripts/WindowSwitcher.sh'
        script.chmod(0o644)
        script.write_text('# modified fixture')
        failures = [msg for ok, msg in self.check() if not ok]
        self.assertTrue(any('executable' in x for x in failures))
        self.assertTrue(any('reinstall' in x for x in failures))

    def test_invalid_json_or_ipc_timeout_reports_without_traceback(self):
        def runner(command, **kwargs):
            if command[1:] == ['-j', 'binds']: return subprocess.CompletedProcess(command, 0, '{broken', '')
            if command[1] == 'eval': raise subprocess.TimeoutExpired(command, 15)
            return self.runner(command, **kwargs)
        failures = [msg for ok, msg in self.check(runner=runner) if not ok]
        self.assertEqual(len(failures), 2, failures)

    def test_no_current_session_is_an_explicit_failure(self):
        self.env.pop('HYPRLAND_INSTANCE_SIGNATURE')
        results = self.check()
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0][0])

    @unittest.skipUnless(shutil.which('lua'), 'Lua needed to exercise read-only handle assertions')
    def test_handle_probe_reads_real_fields_and_rejects_disabled_removed_or_filtered_fixtures(self):
        for damage in ('', 'KOOLDOTS_BINDS["ALT + Tab"].enabled=false',
                       'KOOLDOTS_DEFAULTS.term="alacritty"',
                       'KOOLDOTS_BINDS["SUPER + Return"].description="Hyprixe | SUPER + Return | Alacritty"',
                       'KOOLDOTS_BINDS["ALT + Tab"]=nil',
                       'KOOLDOTS_BINDS["ALT + Tab"].devices={"excluded"}',
                       '''KOOLDOTS_BINDS["ALT + Tab"]=setmetatable({}, {
__tostring=function() return 'HL.Keybind(expired)' end,
__index=function() error('UNSAFE_EXPIRED_HANDLE_ACCESS') end})'''):
            with self.subTest(damage=damage):
                lines = ['HYPRIXE_KEYBINDS_REVISION=1; KOOLDOTS_BINDS={}; KOOLDOTS_DEFAULTS={term="kitty"}',
                         'local original_getenv=os.getenv; os.getenv=function(key) if key=="TERMINAL" then return "kitty" end return original_getenv(key) end']
                for spec in EXPECTED:
                    chord = json.dumps(spec.chord)
                    lines.append(f'KOOLDOTS_BINDS[{chord}]={{enabled=true,display_key={chord},modmask={spec.mask},'
                                 f'submap="",description={json.dumps(PREFIX + spec.chord + (" | Kitty" if spec.chord == "SUPER + Return" else ""))},devices={{}},'
                                 'is_enabled=function(self) return self.enabled end}')
                code = '\n'.join([*lines, damage, handle_probe()])
                result = subprocess.run(['lua', '-'], input=code, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, not damage, result.stderr)
                self.assertNotIn('UNSAFE_EXPIRED_HANDLE_ACCESS', result.stderr)
