"""Read-only evidence for a SDDM -> UWSM -> Hyprland login transition.

No sudo, service changes, process termination or display-manager restart.
Run inside the affected Hyprland session. Missing journal permissions are explicit.
"""
import configparser
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
from session_checks import SESSION_UNITS
from sddm_theme import SystemTheme


def collect(environ=None, runner=None):
    environ = os.environ if environ is None else environ
    runner = subprocess.run if runner is None else runner
    print('Hyprixe login transition diagnostics:', datetime.now(timezone.utc).isoformat())
    print('Kernel:', platform.release())
    print('Session:', {key: environ.get(key, '(unset)') for key in
          ('XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP', 'WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE')})
    try:
        config = SystemTheme().configuration()
        print('Effective SDDM:', {'theme': config.get('Theme', 'Current', fallback='(unset)'),
              'InputMethod': config.get('General', 'InputMethod', fallback='(unset)'),
              'DisplayServer': config.get('General', 'DisplayServer', fallback='x11 (default)')})
    except (OSError, ValueError, configparser.Error) as exc:
        print('UNAVAILABLE: effective SDDM configuration:', exc)

    def query(command, transform=None):
        print('\n$ ' + shlex.join(command), flush=True)
        try:
            result = runner(command, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print('UNAVAILABLE:', exc)
            return
        if result.returncode:
            print(f'UNAVAILABLE/non-active (exit {result.returncode}):', result.stderr.strip())
            if result.stdout.strip():
                print(result.stdout.strip())
            return
        try:
            print(transform(result.stdout) if transform else result.stdout.strip())
        except (ValueError, TypeError, KeyError) as exc:
            print('UNAVAILABLE: cannot parse response:', exc)
        if result.stderr.strip():
            print('NOTICE:', result.stderr.strip())

    query(['journalctl', '-b', '-u', 'sddm', '--no-pager', '-n', '250', '-o', 'short-monotonic'])
    print('If the system journal is restricted, also run: sudo journalctl -b -u sddm --no-pager -o short-monotonic')
    query(['journalctl', '--user', '-b', '--no-pager', '-n', '400', '-o', 'short-monotonic',
           '-u', 'wayland-wm@*', '-u', 'wayland-session@*', '-u', 'hyprixe-*', '-u', 'waybar.service', '-u', 'swaync.service'])
    query(['journalctl', '--user', '-b', '--no-pager', '-n', '250', '-o', 'short-monotonic'])
    query(['systemctl', '--user', 'status', 'graphical-session.target', *SESSION_UNITS, '--no-pager'])
    # Properties remain available even if systemctl status returns nonzero for a failed unit.
    query(['systemctl', '--user', 'show', 'graphical-session.target', *SESSION_UNITS,
           '-p', 'Id', '-p', 'ActiveState', '-p', 'SubState', '-p', 'Result',
           '-p', 'After', '-p', 'Wants', '-p', 'Requires', '-p', 'Requisite',
           '-p', 'InactiveExitTimestampMonotonic', '-p', 'ActiveEnterTimestampMonotonic'])
    query(['systemd-analyze', '--user', 'critical-chain', 'hyprixe-session.target'])
    query(['systemctl', '--user', 'list-units', '--all', '--no-pager', 'app-*@autostart.service'])
    query(['uwsm', 'check', 'is-active', '-v', 'compositor-only'])
    query(['hyprctl', 'version'])
    query(['hyprctl', 'configerrors'])
    query(['hyprctl', 'getoption', 'misc:background_color'])
    query(['hyprctl', 'clients', '-j'], lambda raw: json.dumps([
        {key: client.get(key) for key in ('class', 'initialClass', 'pid', 'mapped', 'fullscreen', 'workspace')}
        for client in json.loads(raw)], indent=2))
    query(['hyprctl', 'layers', '-j'], lambda raw: json.dumps(json.loads(raw), indent=2))
    query(['awww', 'query'])
    print('\nEffective XDG autostart entries (program names only; no command arguments):')
    home = Path(environ.get('HOME', Path.home()))
    state = Path(environ.get('XDG_STATE_HOME', home / '.local/state'))
    startup_log = state / 'hyprixe/session.log'
    print('\nHyprixe compositor startup hook:', startup_log)
    try:
        print('\n'.join(startup_log.read_text().splitlines()[-100:]))
    except (OSError, UnicodeError) as exc:
        print('UNAVAILABLE:', exc)
    config = Path(environ.get('XDG_CONFIG_HOME', home / '.config'))
    roots = [config, *map(Path, environ.get('XDG_CONFIG_DIRS', '/etc/xdg').split(':'))]
    seen = set()
    for root in roots:
        for path in sorted((root / 'autostart').glob('*.desktop')):
            if path.name in seen:
                continue
            seen.add(path.name)
            try:
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read_string(path.read_text())
                entry = parser['Desktop Entry']
                executable = shlex.split(entry.get('Exec', ''))
                print(path, {'program': executable[0] if executable else '',
                      **{key: entry.get(key, '') for key in ('Hidden', 'OnlyShowIn', 'NotShowIn')}})
            except (OSError, ValueError, KeyError, configparser.Error) as exc:
                print('UNAVAILABLE:', path, exc)
    print('\nA current window/layer snapshot cannot identify a window that already disappeared,')
    print('nor prove the color of a displayed frame. Correlate the monotonic journals with the observed flash.')


if __name__ == '__main__':
    collect()
