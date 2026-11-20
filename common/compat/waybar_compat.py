"""Detect and prepare Waybar's workspace IPC and native backlight support."""

from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "scripts"))
from source_layout import ROOT as REPOSITORY_ROOT, source_path, configure_imports, shell_bytes
configure_imports()
import argparse
from pathlib import Path
import shutil
import sys


def replace_once(text, old, new, path):
    if text.count(old) != 1:
        raise ValueError(f'Unexpected Waybar source in {path}; refusing to apply compatibility patch')
    return text.replace(old, new)


def backlight_patch(source):
    """Adapt the pinned 0.12 native module without changing device discovery or logind."""
    module = source / 'src/modules/backlight.cpp'
    backend = source / 'src/util/backlight_backend.cpp'
    header = source / 'include/util/backlight_backend.hpp'
    bar = source / 'src/bar.cpp'
    return {
        module: replace_once(module.read_text(), '''  if (backend.get_scaled_brightness(preferred_device_) <= min_brightness &&
      ct == util::ChangeType::Decrease) {
    return true;
  }
  backend.set_brightness(preferred_device_, ct, step);''', '''  try {
    backend.set_brightness(preferred_device_, ct, step, min_brightness);
  } catch (const Glib::Error& error) {
    spdlog::warn("Backlight adjustment failed: {}", error.what().raw());
  }''', module),
        header: replace_once(header.read_text(),
                             'ChangeType change_type, double step);',
                             'ChangeType change_type, double step, double min_brightness = 0);', header),
        backend: '#include "util/hyprixe_backlight.hpp"\n' + replace_once(backend.read_text(), '''                                      double step) {
  GET_BEST_DEVICE(best, (*this), preferred_device);

  if (best != nullptr) {
    const auto max = best->get_max();

    const auto abs_step = static_cast<int>(round(step * max / 100.0F));

    const int new_brightness = change_type == ChangeType::Increase ? best->get_actual() + abs_step
                                                                   : best->get_actual() - abs_step;
    set_brightness_internal(best->name(), new_brightness, max);
  }''', '''                                      double step, double min_brightness) {
  GET_BEST_DEVICE(best, (*this), preferred_device);

  if (best != nullptr && best->get_max() > 0) {
    const int target = hyprixe::backlightTarget(best->get_actual(), best->get_max(),
        change_type == ChangeType::Increase, step, min_brightness);
    if (target != best->get_actual()) {
      set_brightness_internal(best->name(), target, best->get_max());
    }
  }''', backend),
        # The factory already leaves absent hardware out of the bar. Keep the
        # diagnostic at debug level only for this expected module omission.
        bar: replace_once(bar.read_text(),
                          '        spdlog::warn("module {}: {}", name.asString(), e.what());',
                          '''        if (name.asString() == "backlight" &&
            std::string_view(e.what()) == "Disabling module \\"backlight\\", No backlight found") {
          spdlog::debug("hyprixe-backlight1: no backlight device");
        } else {
          spdlog::warn("module {}: {}", name.asString(), e.what());
        }''', bar),
    }


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
    changes = backlight_patch(source)
    for path, content in changes.items():
        path.write_text(content)
    backend.write_text(code)
    client.write_text(text.replace(original, 'std::cout << "Waybar v" << VERSION << " (hyprixe-lua-ipc1)" << \'\\n\';'))
    shutil.copyfile(Path(__file__).with_name('waybar-lua-ipc.hpp'), source / 'include/util/hyprixe_lua_ipc.hpp')
    shutil.copyfile(Path(__file__).with_name('waybar-backlight.hpp'), source / 'include/util/hyprixe_backlight.hpp')


def has_wlr_taskbar(executable=None):
    executable = executable or shutil.which('waybar')
    if not executable:
        return False
    try:
        data = Path(executable).read_bytes()
    except OSError:
        return False
    return b'wlr/taskbar' in data and b'zwlr_foreign_toplevel_manager_v1' in data


def has_click_drawer(executable=None):
    executable = executable or shutil.which('waybar')
    if not executable:
        return False
    try:
        return b'click-to-reveal' in Path(executable).read_bytes()
    except OSError:
        return False


def has_safe_backlight(executable=None):
    executable = executable or shutil.which('waybar')
    if not executable:
        return False
    try:
        data = Path(executable).read_bytes()
        return all(marker in data for marker in (b'hyprixe-backlight1:', b'min-brightness', b'SetBrightness'))
    except OSError:
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch', metavar='SOURCE')
    args = parser.parse_args()
    if args.patch:
        patch_source(args.patch)
    else:
        sys.exit(0 if all((has_lua_workspace_ipc(), has_wlr_taskbar(), has_click_drawer(),
                           has_safe_backlight())) else 1)
