import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from session_diagnostics import collect


class DiagnosticTests(unittest.TestCase):
    def test_unavailable_commands_produce_report_without_mutations_or_traceback(self):
        output, commands = io.StringIO(), []
        def runner(command, **kwargs):
            commands.append(command)
            raise OSError('unavailable fixture')
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(output):
            collect({'HOME': tmp, 'XDG_CONFIG_DIRS': tmp + '/system'}, runner)
        self.assertIn('UNAVAILABLE', output.getvalue())
        self.assertIn('sudo journalctl', output.getvalue())
        self.assertFalse(any(word in command for command in commands for word in
                             ('start', 'stop', 'restart', 'daemon-reload', 'finalize', 'sudo')))

    def test_current_clients_exclude_titles_and_autostart_arguments(self):
        output = io.StringIO()
        def runner(command, **kwargs):
            value = ''
            if command[:2] == ['hyprctl', 'clients']:
                value = '[{"class":"example","fullscreen":2,"title":"PRIVATE_WINDOW_TITLE"}]'
            elif command[:2] == ['hyprctl', 'layers']:
                value = '{}'
            elif command == ['hyprctl', '-j', 'binds']:
                value = '[{"key":"F10","dispatcher":"exec","arg":"PRIVATE_BIND_ARGUMENT"}]'
            return subprocess.CompletedProcess(command, 0, value, '')
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(output):
            autostart = Path(tmp) / '.config/autostart/example.desktop'
            autostart.parent.mkdir(parents=True)
            autostart.write_text('[Desktop Entry]\nExec=example --argument PRIVATE_ARGUMENT\nOnlyShowIn=Hyprland;\n')
            collect({'HOME': tmp, 'XDG_CONFIG_DIRS': tmp + '/system'}, runner)
        self.assertIn('example', output.getvalue())
        self.assertNotIn('PRIVATE_WINDOW_TITLE', output.getvalue())
        self.assertNotIn('PRIVATE_ARGUMENT', output.getvalue())
        self.assertNotIn('PRIVATE_BIND_ARGUMENT', output.getvalue())
        self.assertIn('cannot identify a window that already disappeared', output.getvalue())
