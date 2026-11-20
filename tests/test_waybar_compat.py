import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
from support import source_path, configure_imports, shell_bytes
configure_imports()

spec = importlib.util.spec_from_file_location('waybar_compat', source_path(ROOT, 'scripts/waybar_compat.py'))
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)


class CapabilityTests(unittest.TestCase):
    def test_stock_backlight_capability_does_not_claim_safe_scroll(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'waybar'
            binary.write_bytes(b'min-brightness\0SetBrightness')
            self.assertFalse(compat.has_safe_backlight(binary))
            binary.write_bytes(binary.read_bytes() + b'\0hyprixe-backlight1: no backlight device')
            self.assertTrue(compat.has_safe_backlight(binary))

    def test_native_click_drawer_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'waybar'
            binary.write_bytes(b'old group drawer')
            self.assertFalse(compat.has_click_drawer(binary))
            binary.write_bytes(b'click-to-reveal')
            self.assertTrue(compat.has_click_drawer(binary))
            self.assertFalse(compat.has_click_drawer(Path(tmp) / 'missing'))

    def test_legacy_and_lua_capabilities(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'waybar'
            binary.write_bytes(b'dispatch workspace \0dispatch togglespecialworkspace')
            self.assertFalse(compat.has_lua_workspace_ipc(binary))
            binary.write_bytes(b'hl.dsp.focus({ workspace\0hl.dsp.workspace.toggle_special(')
            self.assertTrue(compat.has_lua_workspace_ipc(binary))
            self.assertFalse(compat.has_lua_workspace_ipc(Path(tmp) / 'missing'))

    def test_taskbar_requires_compiled_module_and_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'waybar'
            binary.write_bytes(b'wlr/taskbar')
            self.assertFalse(compat.has_wlr_taskbar(binary))
            binary.write_bytes(b'wlr/taskbar\0zwlr_foreign_toplevel_manager_v1')
            self.assertTrue(compat.has_wlr_taskbar(binary))
            self.assertFalse(compat.has_wlr_taskbar(Path(tmp) / 'missing'))


@unittest.skipUnless(shutil.which('g++'), 'C++ compiler required to exercise native scroll arithmetic')
class BacklightTargetTests(unittest.TestCase):
    def test_floor_bounds_and_coarse_hardware(self):
        source = '''#include "waybar-backlight.hpp"
using hyprixe::backlightTarget;
int main() {
  if (backlightTarget(65, 100, true, 5, 5) != 70 ||
      backlightTarget(65, 100, false, 5, 5) != 60 ||
      backlightTarget(6, 100, false, 5, 5) != 5 ||
      backlightTarget(5, 100, false, 5, 5) != 5 ||
      backlightTarget(8, 101, false, 5, 5) != 6 ||
      backlightTarget(98, 100, true, 5, 5) != 100) return 1;
  if (backlightTarget(1, 10, false, 5, 5) != 1 ||
      backlightTarget(2, 7, false, 5, 5) != 1 ||
      backlightTarget(1, 7, true, 5, 5) != 2 ||
      backlightTarget(0, 100, false, 5, 5) != 0 ||
      backlightTarget(0, 100, true, 5, 5) != 5 ||
      backlightTarget(0, 0, true, 5, 5) != 0) return 2;
}
'''
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / 'backlight-target'
            subprocess.run(['g++', '-std=c++20', '-x', 'c++', '-I', str(ROOT / 'common/compat'),
                            '-o', str(binary), '-'], input=source, text=True, check=True)
            subprocess.run([str(binary)], check=True)


@unittest.skipUnless(shutil.which('g++') and shutil.which('lua'), 'C++ compiler and Lua required for IPC compatibility tests')
class WorkspaceProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='hyprixe-waybar-test-')
        cls.root = Path(cls.temp.name)
        source = cls.root / 'request.cpp'
        source.write_text('#include "waybar-lua-ipc.hpp"\n#include <iostream>\nint main(int argc,char** argv) { if(argc!=2) return 2; std::cout << hyprixe::waybarLuaRequest(argv[1]); }\n')
        cls.exe = cls.root / 'request'
        subprocess.run(['g++', '-std=c++20', '-I', str(ROOT / 'common/compat'), str(source), '-o', str(cls.exe)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def request(self, command):
        return subprocess.check_output([str(self.exe), command], text=True)

    def evaluate(self, command):
        translated = self.request(command)
        self.assertTrue(translated.startswith('/dispatch '))
        # Hyprland 0.56.2 wraps dispatch requests in return hl.dispatch(...).
        script = '''hl = { dsp = { focus = function(opts) return opts end,
          workspace = { toggle_special = function(name) return { special = name or "default" } end } },
          dispatch = function(value) return value end }
local result = assert(load("return hl.dispatch(" .. arg[1] .. ")"))()
if result.workspace then io.write(result.workspace) end
if result.on_current_monitor then io.write("@current") end
if result.special then io.write(result.special) end
'''
        path = self.root / 'evaluate.lua'
        path.write_text(script)
        return subprocess.check_output(['lua', str(path), translated[len('/dispatch '):]], text=True)

    def test_numbered_workspace(self):
        self.assertEqual(self.evaluate('dispatch workspace 3'), '3')

    def test_named_workspace_escaping_preserves_data(self):
        name = 'name:notes "quoted"\\path\nline'
        self.assertEqual(self.evaluate('dispatch workspace ' + name), name)

    def test_current_monitor_workspace(self):
        self.assertEqual(self.evaluate('dispatch focusworkspaceoncurrentmonitor 2'), '2@current')

    def test_special_workspaces(self):
        self.assertEqual(self.evaluate('dispatch togglespecialworkspace'), 'default')
        self.assertEqual(self.evaluate('dispatch togglespecialworkspace scratch'), 'scratch')

    def test_read_only_queries_unchanged(self):
        for query in ('j/workspaces', 'j/clients', 'j/activewindow', 'j/monitors', 'systeminfo'):
            self.assertEqual(self.request(query), query)


if __name__ == '__main__': unittest.main()
