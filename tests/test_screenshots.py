"""Capture/clipboard commands are explicit mocks; files and collisions are real."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.config/hypr/scripts/ScreenShot.sh'
PNG = b'\x89PNG\r\n\x1a\nmock capture bytes'
MOCK = '''#!/usr/bin/python3
import json, os, pathlib, sys
root=pathlib.Path(os.environ['SCREENSHOT_TEST_ROOT'])
name=pathlib.Path(sys.argv[0]).name
with (root/'calls').open('a') as log: log.write(json.dumps([name]+sys.argv[1:])+'\\n')
if name=='date': print('2026-10-26_21-30-15')
elif name=='slurp':
 if os.environ.get('CANCEL'): sys.exit(1)
 print('10,20 300x200')
elif name=='grim':
 if os.environ.get('GRIM_FAIL'): sys.exit(1)
 if not os.environ.get('GRIM_EMPTY'): pathlib.Path(sys.argv[-1]).write_bytes(b'\\x89PNG\\r\\n\\x1a\\nmock capture bytes')
elif name=='wl-copy':
 if os.environ.get('COPY_FAIL'): sys.exit(1)
 (root/'clipboard').write_bytes(sys.stdin.buffer.read())
elif name=='xdg-user-dir': print(root/'home with spaces/Images')
elif name=='swappy':
 if not os.environ.get('EDITOR_CANCEL'):
  pathlib.Path(sys.argv[-1]).write_bytes(pathlib.Path(sys.argv[2]).read_bytes())
'''


class ScreenshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe-screenshot-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home with spaces'
        self.home.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.scratch = self.root / 'tmp'
        self.scratch.mkdir()
        for command in ('grim', 'slurp', 'wl-copy', 'xdg-user-dir', 'notify-send', 'swappy', 'sleep', 'date'):
            executable = self.bin / command
            executable.write_text(MOCK)
            executable.chmod(0o755)
        (self.root / 'clipboard').write_bytes(b'previous clipboard')
        self.env = dict(os.environ, HOME=str(self.home), TMPDIR=str(self.scratch),
                        SCREENSHOT_TEST_ROOT=str(self.root), PATH=str(self.bin) + ':' + os.environ['PATH'])

    def capture(self, mode, **changes):
        result = subprocess.run(['bash', str(SCRIPT), mode], capture_output=True, text=True,
                                env=dict(self.env, **changes), timeout=10)
        self.assertEqual(list(self.scratch.iterdir()), [], 'temporary captures must be cleaned up')
        return result

    def calls(self):
        path = self.root / 'calls'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_area_copy_uses_png_clipboard_without_persistent_file(self):
        result = self.capture('--copy-area')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / 'clipboard').read_bytes(), PNG)
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(next(c for c in self.calls() if c[0] == 'grim')[1:3], ['-g', '10,20 300x200'])
        self.assertIn(['wl-copy', '--type', 'image/png'], self.calls())

    def test_full_save_creates_requested_directory_without_touching_clipboard(self):
        result = self.capture('--save')
        self.assertEqual(result.returncode, 0, result.stderr)
        files = list((self.home / 'Pictures/Screenshots').glob('*.png'))
        self.assertEqual(len(files), 1)
        self.assertRegex(files[0].name, r'^Screenshot-2026-10-26_21-30-15-[A-Za-z0-9]{6}\.png$')
        self.assertEqual(files[0].read_bytes(), PNG)
        self.assertEqual((self.root / 'clipboard').read_bytes(), b'previous clipboard')
        self.assertFalse(any(c[0] in ('slurp', 'wl-copy', 'xdg-user-dir') for c in self.calls()))

    def test_selected_area_save_is_separate_from_clipboard_copy(self):
        result = self.capture('--save-area')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list((self.home / 'Pictures/Screenshots').glob('*.png'))), 1)
        self.assertEqual((self.root / 'clipboard').read_bytes(), b'previous clipboard')
        self.assertEqual(next(c for c in self.calls() if c[0] == 'grim')[1:3], ['-g', '10,20 300x200'])

    def test_cancelled_selection_changes_no_clipboard_or_directory(self):
        for mode in ('--copy-area', '--save-area', '--area'):
            with self.subTest(mode=mode):
                result = self.capture(mode, CANCEL='1')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(list(self.home.iterdir()), [])
                self.assertEqual((self.root / 'clipboard').read_bytes(), b'previous clipboard')
        self.assertFalse(any(c[0] in ('grim', 'wl-copy') for c in self.calls()))

    def test_failed_or_empty_capture_does_not_replace_clipboard_or_save(self):
        for changes in ({'GRIM_FAIL': '1'}, {'GRIM_EMPTY': '1'}):
            for mode in ('--save', '--copy-area'):
                with self.subTest(mode=mode, changes=changes):
                    self.assertNotEqual(self.capture(mode, **changes).returncode, 0)
                    self.assertEqual((self.root / 'clipboard').read_bytes(), b'previous clipboard')
                    self.assertEqual(list(self.home.iterdir()), [])

    def test_concurrent_same_second_saves_do_not_overwrite(self):
        jobs = [subprocess.Popen(['bash', str(SCRIPT), '--save'], env=self.env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(4)]
        for job in jobs:
            _, error = job.communicate(timeout=10)
            self.assertEqual(job.returncode, 0, error)
        files = list((self.home / 'Pictures/Screenshots').glob('*.png'))
        self.assertEqual(len(files), 4)
        self.assertTrue(all(p.read_bytes() == PNG for p in files))
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_legacy_modes_still_save_in_xdg_pictures_and_copy(self):
        for mode in ('--now', '--area', '--swappy', '--in5'):
            with self.subTest(mode=mode):
                result = self.capture(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((self.root / 'clipboard').read_bytes(), PNG)
        files = list((self.home / 'Images/Screenshots').glob('*.png'))
        self.assertEqual(len(files), 4)
        self.assertTrue(all(p.read_bytes() == PNG for p in files))

    def test_clipboard_error_is_nonzero(self):
        self.assertNotEqual(self.capture('--copy-area', COPY_FAIL='1').returncode, 0)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_cancelled_editor_leaves_no_empty_saved_file(self):
        result = self.capture('--swappy', EDITOR_CANCEL='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list((self.home / 'Images/Screenshots').iterdir()), [])
        self.assertEqual((self.root / 'clipboard').read_bytes(), b'previous clipboard')

    def test_unknown_mode_has_no_side_effects(self):
        self.assertEqual(self.capture('--unknown').returncode, 2)
        self.assertEqual(self.calls(), [])
        self.assertEqual(list(self.home.iterdir()), [])
