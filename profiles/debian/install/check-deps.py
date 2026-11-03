"""Check actual executable capabilities before changing any user configuration."""

from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "scripts"))
from source_layout import ROOT as REPOSITORY_ROOT, source_path, configure_imports, shell_bytes
configure_imports()
from pathlib import Path
import shutil
import subprocess
import sys
from waybar_compat import has_lua_workspace_ipc, has_wlr_taskbar, has_click_drawer
from rofi_compat import has_wayland_support
from rofi_launcher import has_launcher_actions, has_launcher_cover
from dolphin_checks import runtime_errors as dolphin_runtime_errors
from terminal_checks import runtime_errors as terminal_runtime_errors, config_errors as terminal_config_errors
from wlogout_checks import runtime_errors as wlogout_runtime_errors
from interactive_shell import dependencies as shell_dependencies
from hyprland_version import assess

commands = ('Hyprland', 'hyprctl', 'uwsm', 'hyprlock', 'hypridle', 'kitty', 'dolphin',
            'waybar', 'wlogout', 'rofi', 'awww', 'awww-daemon', 'jq', 'flock', 'wpctl',
            'wl-paste', 'wl-copy', 'cliphist', 'swaync', 'nm-connection-editor',
            'blueman-manager', 'pavucontrol', 'playerctl', 'brightnessctl',
            'grim', 'slurp', 'xdg-user-dir', 'dbus-update-activation-environment')
missing = [c for c in commands if not shutil.which(c)]
errors = []
if missing:
    errors.append('Missing commands: ' + ', '.join(missing))
if not Path('/usr/share/wayland-sessions/hyprland-uwsm.desktop').is_file():
    errors.append('Debian Hyprland UWSM session entry is missing; install the Hyprland package from trixie-backports.')
for name in ('rofi', 'waybar', 'awww', 'awww-daemon'):
    print(f'INFO: {name}: {shutil.which(name) or "not found in PATH"}', flush=True)
if shutil.which('waybar') and not has_lua_workspace_ipc():
    errors.append('Waybar lacks Lua workspace IPC support; run ./install.sh to prepare the compatible build.')
if shutil.which('waybar') and not has_wlr_taskbar():
    errors.append('Waybar lacks wlr/taskbar support; run ./install.sh to prepare the compatible build.')
if shutil.which('waybar') and not has_click_drawer():
    errors.append('Waybar lacks native click drawer support; run ./install.sh to prepare the compatible build.')
if shutil.which('Hyprland'):
    result = subprocess.run(['Hyprland', '--version'], capture_output=True, text=True)
    version = assess(result.stdout + result.stderr, result.returncode)
    if not version.allowed:
        errors.append(version.message)
    else:
        print('INFO: ' + version.message, flush=True)
        if version.warning:
            print('WARNING: ' + version.warning, flush=True)
if shutil.which('rofi') and not has_wayland_support():
    errors.append('Rofi must include Wayland support (rofi 2.x or rofi-wayland); run ./install.sh native to prepare it.')
if shutil.which('rofi') and not has_launcher_actions(shutil.which('rofi')):
    errors.append('Rofi lacks Hyprixe launcher button support; run ./install.sh native (without --no-packages) to prepare it.')
if shutil.which('rofi') and not has_launcher_cover(shutil.which('rofi')):
    errors.append('Rofi lacks adaptive launcher wallpaper cropping; run ./install.sh native (without --no-packages) to prepare it.')
kvantum = list(__import__('pathlib').Path('/usr/lib').glob('**/qt6/plugins/styles/libkvantum.so'))
if not kvantum:
    errors.append('Qt6 Kvantum plugin not found; install qt6-style-kvantum.')
errors.extend(dolphin_runtime_errors())
errors.extend(terminal_runtime_errors())
errors.extend(wlogout_runtime_errors())
errors.extend(shell_dependencies())
if shutil.which('kitty'):
    errors.extend(terminal_config_errors(source_path(REPOSITORY_ROOT, '.config/kitty/kitty.conf')))
for error in errors:
    print('ERROR: ' + error, file=sys.stderr)
if errors:
    sys.exit(1)
print('PASS: runtime dependencies, Hyprland version, Rofi Wayland and Qt6 Kvantum plugin')
