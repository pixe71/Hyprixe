"""Check actual executable capabilities before changing any user configuration."""
import re
import os
import shutil
import subprocess
import sys
from waybar_compat import has_lua_workspace_ipc

commands = ('Hyprland', 'hyprctl', 'hyprlock', 'hypridle', 'alacritty', 'dolphin',
            'waybar', 'rofi', 'awww', 'awww-daemon', 'jq', 'flock', 'wpctl',
            'wl-paste', 'wl-copy', 'cliphist', 'swaync', 'nm-connection-editor',
            'blueman-manager', 'pavucontrol', 'playerctl', 'brightnessctl',
            'grim', 'slurp', 'xdg-user-dir', 'dbus-update-activation-environment')
missing = [c for c in commands if not shutil.which(c)]
errors = []
if missing:
    errors.append('Missing commands: ' + ', '.join(missing))
if shutil.which('waybar') and not has_lua_workspace_ipc():
    errors.append('Waybar lacks Lua workspace IPC support; run ./install.sh to prepare the compatible build.')
if shutil.which('Hyprland'):
    result = subprocess.run(['Hyprland', '--version'], capture_output=True, text=True)
    match = re.search(r'\b(\d+)\.(\d+)\.(\d+)', result.stdout + result.stderr)
    if result.returncode or not match or tuple(map(int, match.groups())) < (0, 55, 2):
        errors.append('Hyprland >= 0.55.2 is required for the Lua configuration.')
if shutil.which('rofi'):
    probe = dict(os.environ, WAYLAND_DISPLAY='hyprixe-capability-probe', DISPLAY='')
    result = subprocess.run(['rofi', '-info'], capture_output=True, text=True, env=probe)
    version = subprocess.run(['rofi', '-version'], capture_output=True, text=True)
    capabilities = result.stdout + '\n' + version.stdout
    if not re.search(r'wayland\s+enabled|wayland:.*selected|Version.*wayland', capabilities, re.I):
        errors.append('Rofi must include Wayland support (rofi 2.x or rofi-wayland).')
kvantum = list(__import__('pathlib').Path('/usr/lib').glob('**/qt6/plugins/styles/libkvantum.so'))
if not kvantum:
    errors.append('Qt6 Kvantum plugin not found; install qt6-style-kvantum.')
for error in errors:
    print('ERROR: ' + error, file=sys.stderr)
if errors:
    sys.exit(1)
print('PASS: runtime dependencies, Hyprland version, Rofi Wayland and Qt6 Kvantum plugin')
