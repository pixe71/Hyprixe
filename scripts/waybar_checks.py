"""Waybar organization checks; optional hardware is handled by native modules."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from waybar_compat import has_click_drawer, has_lua_workspace_ipc, has_wlr_taskbar

LEFT = ['group/traygroup', 'hyprland/workspaces', 'wlr/taskbar']
CENTER = ['custom/temperature', 'memory', 'cpu', 'custom/distro', 'clock#time', 'clock#date', 'idle_inhibitor']
RIGHT = ['network', 'bluetooth', 'pulseaudio', 'battery', 'custom/power']


def validate(config, root):
    for side, expected in (('left', LEFT), ('center', CENTER), ('right', RIGHT)):
        if config['modules-' + side] != expected:
            raise ValueError('Unexpected ' + side + ' module order')
    if config.get('fixed-center') is not True or config['height'] != 31:
        raise ValueError('Keep fixed-center and the existing 31 px height')
    group = config['group/traygroup']
    if group['drawer'].get('click-to-reveal') is not True or group['modules'][:2] != ['custom/traylauncher', 'tray']:
        raise ValueError('Native click tray drawer missing')
    if config['hyprland/workspaces']['persistent-workspaces'] != {'*': [1, 2, 3, 4]}:
        raise ValueError('Keep exactly four persistent workspaces without an output name')
    if config['hyprland/workspaces'].get('ignore-workspaces') != ['^(?![1-4]$).*$']:
        raise ValueError('Only workspaces 1 to 4 should be shown on the bar')
    if any(key in config['battery'] for key in ('bat', 'adapter')):
        raise ValueError('Battery and AC adapter must be discovered automatically')
    if '{capacity}%' not in config['battery']['format'] or 'on-click' in config['custom/distro']:
        raise ValueError('Battery percentage required; Debian logo has no click action')
    for name in ('mpris', 'hyprland/window', 'hyprland/submap'):
        if name not in group['modules']:
            raise ValueError('Existing status module lost: ' + name)
    if not (root / 'scripts/temperature.py').is_file():
        raise ValueError('Adaptive CPU temperature / root storage helper missing')


def check_source(report, repo):
    try:
        root = Path(repo) / '.config/hypr/waybar'
        config = json.loads((root / 'configs/Frosted-Glass').read_text())
        validate(config, root)
        font = Path(repo) / '.local/share/fonts/hyprixe/HyprixeDebian.ttf'
        if not font.is_file() or font.read_bytes()[:4] != b'\x00\x01\x00\x00':
            raise ValueError('Bundled Debian logo font missing/invalid')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report(False, 'Waybar organization: ' + str(exc))
    else:
        report(True, 'Waybar layout: native tray drawer, four workspaces, centered Debian, adaptive sensor and automatic battery')


def check_installed(report):
    home = Path.home()
    root = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'hypr/waybar'
    try:
        validate(json.loads((root / 'configs/Frosted-Glass').read_text()), root)
        if not (root / 'style.css').is_file() or not (root / 'style/Frosted-Glass.css').is_file():
            raise ValueError('Active Waybar CSS missing')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report(False, 'Installed Waybar organization: ' + str(exc))
    else:
        report(True, 'Installed Waybar configuration, CSS and adaptive helper exist')
    binary = shutil.which('waybar')
    report(has_lua_workspace_ipc(binary) and has_wlr_taskbar(binary) and has_click_drawer(binary),
           'Installed Waybar supports Lua workspace IPC, taskbar and native click drawer')
    try:
        font = subprocess.run(['fc-match', '-f', '%{family}', 'Hyprixe Debian:charset=f306'],
                              capture_output=True, text=True, timeout=10)
        report(font.returncode == 0 and font.stdout == 'Hyprixe Debian', 'Debian logo glyph resolves with its isolated font family')
    except (OSError, subprocess.TimeoutExpired) as exc:
        report(False, 'Debian logo font: ' + str(exc))
    print('SKIPPED: tray clicks, idle inhibition, real sensors/battery and visual balance require a live desktop test')
