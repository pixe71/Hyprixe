"""Detect Waybar's required taskbar/Lua capabilities; patch only workspace IPC."""
import argparse
from pathlib import Path
import shutil
import sys


def has_lua_workspace_ipc(executable=None):
    executable = executable or shutil.which('waybar')
    if not executable:
        return False
    try:
        data = Path(executable).read_bytes()
    except OSError:
        return False
    # Present in our compatibility build and upstream's native Lua IPC backend.
    return b'hl.dsp.focus({ workspace' in data and b'hl.dsp.workspace.toggle_special(' in data


def patch_source(source):
    source = Path(source)
    backend = source / 'src/modules/hyprland/backend.cpp'
    client = source / 'src/client.cpp'
    old = 'auto sizeWritten = write(serverSocket, rq.c_str(), rq.length());'
    code = backend.read_text()
    if code.count(old) != 1:
        raise ValueError('Unexpected Waybar backend source; refusing to apply compatibility patch')
    code = '#include "util/hyprixe_lua_ipc.hpp"\n' + code
    code = code.replace(old, 'const auto request = hyprixe::waybarLuaRequest(rq);\n  auto sizeWritten = write(serverSocket, request.c_str(), request.length());')
    original = 'std::cout << "Waybar v" << VERSION << \'\\n\';'
    text = client.read_text()
    if text.count(original) != 1:
        raise ValueError('Unexpected Waybar version output; refusing to apply compatibility patch')
    backend.write_text(code)
    client.write_text(text.replace(original, 'std::cout << "Waybar v" << VERSION << " (hyprixe-lua-ipc1)" << \'\\n\';'))
    shutil.copyfile(Path(__file__).with_name('waybar-lua-ipc.hpp'), source / 'include/util/hyprixe_lua_ipc.hpp')


def has_wlr_taskbar(executable=None):
    executable = executable or shutil.which('waybar')
    if not executable:
        return False
    try:
        data = Path(executable).read_bytes()
    except OSError:
        return False
    return b'wlr/taskbar' in data and b'zwlr_foreign_toplevel_manager_v1' in data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch', metavar='SOURCE')
    args = parser.parse_args()
    if args.patch:
        patch_source(args.patch)
    else:
        sys.exit(0 if has_lua_workspace_ipc() and has_wlr_taskbar() else 1)
