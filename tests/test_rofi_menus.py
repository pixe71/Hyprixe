"""Shared native Rasi contracts and clipboard regressions with isolated data."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
from support import source_path, configure_imports, shell_bytes
configure_imports()

sys.path.insert(0, str(ROOT / 'scripts'))
from rofi_compat import has_wayland_support


def theme_blocks(text):
    return {name.strip(): {key: value.strip() for key, value in re.findall(r'^\s*([\w-]+):\s*(.*?);\s*$', body, re.M)}
            for name, body in re.findall(r'^([^{}\n]+)\s*\{\n(.*?)^\}', text, re.S | re.M)}


@unittest.skipUnless(shutil.which('rofi') and has_wayland_support(), 'native Wayland Rofi parser required')
class SharedThemeTests(unittest.TestCase):
    def test_all_active_menus_share_paint_search_selection_and_fonts(self):
        themes = {}
        for name in ('config-launcher', 'config-windows', 'config-clipboard', 'config-calc', 'config'):
            result = subprocess.run(['rofi', '-config', str(source_path(ROOT, '.config/hypr/rofi') / (name + '.rasi')),
                                     '-dump-theme'], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('Black/', result.stdout)
            themes[name] = theme_blocks(result.stdout)
            settings = subprocess.run(['rofi', '-config', str(source_path(ROOT, '.config/hypr/rofi') / (name + '.rasi')),
                                       '-dump-config'], capture_output=True, text=True, timeout=15)
            self.assertEqual(settings.returncode, 0, settings.stderr)
            self.assertRegex(settings.stdout, r'\bfont:\s*"JetBrains Mono SemiBold 13";')
        reference = themes['config-launcher']
        for name, theme in themes.items():
            with self.subTest(menu=name):
                for selector, properties in {
                    '*': ('launcher-glass', 'launcher-input', 'launcher-selection', 'launcher-hover', 'launcher-edge'),
                    'window': ('background-color', 'border', 'border-color', 'border-radius'),
                    'mainbox': ('background-color',),
                    'inputbar': ('background-color', 'border', 'border-color', 'border-radius', 'padding'),
                    'entry': ('background-color', 'text-color'),
                    'listview': ('background-color', 'border-color', 'border-radius'),
                    'element normal.normal': ('background-color', 'text-color'),
                    'element alternate.normal': ('background-color', 'text-color'),
                    'element selected.normal': ('background-color', 'text-color'),
                    'element-text': ('background-color',),
                }.items():
                    for prop in properties:
                        self.assertEqual(theme[selector][prop], reference[selector][prop], (name, selector, prop))
                self.assertEqual(theme['mainbox']['background-color'], 'transparent')
        windows = themes['config-windows']
        for selector, prop in (('window', 'width'), ('window', 'height'), ('wallpaper-panel', 'background-image'),
                               ('wallpaper-panel', 'width'), ('mainbox', 'children')):
            self.assertEqual(windows[selector][prop], reference[selector][prop])
        self.assertEqual(windows['button-windows']['action'], '""')
        self.assertEqual(windows['button-windows']['background-color'], 'var(launcher-selection)')
        self.assertEqual(reference['button-applications']['background-color'], 'var(launcher-selection)')
        self.assertEqual(themes['config-clipboard']['window']['width'], '42.0000%')
        self.assertNotIn('wallpaper-panel', themes['config-clipboard']['mainbox']['children'])


MOCK = r'''#!/usr/bin/python3
import json,os,pathlib,sys
root=pathlib.Path(os.environ['MOCK_ROOT']);name=pathlib.Path(sys.argv[0]).name
with (root/'calls').open('a') as f:f.write(json.dumps([name]+sys.argv[1:])+'\n')
if name=='cliphist':
 if sys.argv[1]=='list':print('1\tFirst entry\n2\tSecond entry')
 elif sys.argv[1]=='decode':
  (root/'decoded-entry').write_text(sys.stdin.read())
  sys.stdout.buffer.write(b'clipboard payload')
 elif sys.argv[1]=='delete':(root/'deleted-entry').write_text(sys.stdin.read())
elif name=='rofi':
 (root/'rofi-input').write_text(sys.stdin.read())
 state=root/'rofi-count';index=int(state.read_text()) if state.exists() else 0;state.write_text(str(index+1))
 replies=json.loads(os.environ.get('MOCK_REPLIES','[[0,"1\tFirst entry"]]'))
 code,text=replies[index];print(text);sys.exit(code)
elif name=='wl-copy' and '--clear' not in sys.argv:(root/'clipboard').write_bytes(sys.stdin.buffer.read())
'''


class ClipboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe clipboard ')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        bins = self.home / 'bin'
        bins.mkdir()
        for name in ('rofi', 'cliphist', 'wl-copy', 'pkill', 'notify-send'):
            path = bins / name
            path.write_text(MOCK)
            path.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / 'settings with spaces'),
                        MOCK_ROOT=str(self.home), PATH=str(bins) + ':' + os.environ['PATH'])

    def run_clipboard(self, replies):
        self.env['MOCK_REPLIES'] = json.dumps(replies)
        return subprocess.run(['bash', str(source_path(ROOT, '.config/hypr/scripts/ClipManager.sh'))],
                              env=self.env, capture_output=True, text=True, timeout=15)

    def calls(self):
        return [json.loads(line) for line in (self.home / 'calls').read_text().splitlines()]

    def test_selected_entry_is_decoded_and_copied_with_compact_xdg_theme(self):
        result = self.run_clipboard([[0, '2\tSecond entry']])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home / 'decoded-entry').read_text(), '2\tSecond entry')
        self.assertEqual((self.home / 'clipboard').read_bytes(), b'clipboard payload')
        rofi = next(c for c in self.calls() if c[0] == 'rofi')
        self.assertIn(str(self.home / 'settings with spaces/hypr/rofi/config-clipboard.rasi'), rofi)
        self.assertIn('-no-custom', rofi)

    def test_image_entry_preserves_its_mime_type(self):
        result = self.run_clipboard([[0, '3\t[[ binary data 1 KiB png 2x2 ]]']])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(['wl-copy', '--type', 'image/png'], self.calls())

    def test_cancel_and_errors_leave_the_clipboard_untouched(self):
        for code in (1, 17):
            with self.subTest(code=code):
                (self.home / 'rofi-count').unlink(missing_ok=True)
                (self.home / 'calls').write_text('')
                result = self.run_clipboard([[code, '1\tFirst entry']])
                self.assertEqual(result.returncode, 0 if code == 1 else 1)
                self.assertFalse(any(c[0] == 'wl-copy' for c in self.calls()))

    def test_delete_and_wipe_keep_the_existing_custom_actions(self):
        for code in (10, 11):
            with self.subTest(code=code):
                (self.home / 'rofi-count').unlink(missing_ok=True)
                (self.home / 'calls').write_text('')
                result = self.run_clipboard([[code, '1\tFirst entry'], [1, '']])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(['cliphist', 'delete' if code == 10 else 'wipe'], self.calls())
                if code == 11:
                    self.assertIn(['wl-copy', '--clear'], self.calls())
