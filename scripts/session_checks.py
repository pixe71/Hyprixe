"""Read-only checks for the UWSM/systemd lifecycle of a Hyprixe session."""
import os
import configparser
from pathlib import Path
import subprocess

SESSION_UNITS = ('hyprixe-session.target', 'waybar.service', 'hypridle.service',
                 'swaync.service', 'hyprixe-awww.service', 'hyprixe-wallpaper.service',
                 'hyprixe-clipboard.service', 'hyprixe-polkit.service')
LOGIN_HINT = 'Log out and select "Hyprland (uwsm-managed)" in SDDM, then log in again.'


def check_source_order(units):
    """Check our explicit ordering; never infer it just from Wants= membership."""
    rules = {
        'hyprixe-session.target': {'Wants': {'hyprixe-wallpaper.service', 'waybar.service'}},
        'hyprixe-awww.service': {'After': {'graphical-session.target'}, 'PartOf': {'graphical-session.target'}},
        'hyprixe-wallpaper.service': {'Requires': {'hyprixe-awww.service'},
            'After': {'graphical-session.target', 'hyprixe-awww.service'},
            'Before': {'waybar.service', 'swaync.service'}, 'PartOf': {'graphical-session.target'}},
        'waybar.service.d/hyprixe.conf': {'Wants': {'hyprixe-wallpaper.service'}, 'After': {'hyprixe-wallpaper.service'}},
        'swaync.service.d/hyprixe.conf': {'Wants': {'hyprixe-wallpaper.service'}, 'After': {'hyprixe-wallpaper.service'}},
    }
    failures = []
    for name, keys in rules.items():
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        try:
            parser.read_string((Path(units) / name).read_text())
            for key, expected in keys.items():
                if not expected.issubset(set(parser.get('Unit', key, fallback='').split())):
                    failures.append(f'{name}: {key} must include {" ".join(sorted(expected))}')
        except (OSError, configparser.Error) as exc:
            failures.append(f'{name}: {exc}')
    return failures


def check_session(report, environ=None, runner=None):
    environ = os.environ if environ is None else environ
    runner = subprocess.run if runner is None else runner

    def query(command):
        try:
            return runner(command, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return subprocess.CompletedProcess(command, 1, '', str(exc))

    if not environ.get('HYPRLAND_INSTANCE_SIGNATURE') or not environ.get('WAYLAND_DISPLAY'):
        report(False, 'No current Hyprland environment. Run --session from a terminal inside the session. ' + LOGIN_HINT)
        return False
    managed = query(['uwsm', 'check', 'is-active', 'compositor-only']).returncode == 0
    report(managed, 'UWSM compositor is active' if managed else 'Hyprland is not managed by UWSM. ' + LOGIN_HINT)
    target = query(['systemctl', '--user', 'show', 'graphical-session.target', '-p', 'ActiveState', '--value'])
    active = target.returncode == 0 and target.stdout.strip() == 'active'
    report(active, 'graphical-session.target is active' if active else
           'graphical-session.target is not active; Debian Waybar Requisite= cannot be satisfied. '
           'Importing WAYLAND_DISPLAY alone does not activate a session. ' + LOGIN_HINT)
    if not managed or not active:
        return False

    manager = query(['systemctl', '--user', 'show-environment'])
    if manager.returncode:
        report(False, 'Cannot read the systemd user activation environment: ' + manager.stderr.strip())
        return False
    values = dict(line.split('=', 1) for line in manager.stdout.splitlines() if '=' in line)
    matches = all(values.get(name) == environ.get(name)
                  for name in ('WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE'))
    matches = matches and 'Hyprland' in values.get('XDG_CURRENT_DESKTOP', '').split(':')
    report(matches, 'systemd activation environment matches the current Hyprland session' if matches else
           'systemd activation environment is missing or stale; check UWSM finalization and log in again')
    ok = matches
    states = {}
    for unit in SESSION_UNITS:
        result = query(['systemctl', '--user', 'show', unit, '-p', 'ActiveState', '-p', 'Result',
                        '-p', 'After', '-p', 'Wants', '-p', 'Requires',
                        '-p', 'InactiveExitTimestampMonotonic', '-p', 'ActiveEnterTimestampMonotonic'])
        state = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        states[unit] = state
        running = result.returncode == 0 and state.get('ActiveState') == 'active'
        if not running and unit == 'hyprixe-polkit.service':
            # An XDG-autostarted agent can legitimately make our duplicate guard exit.
            agent = query(['pgrep', '-u', str(os.getuid()), '-f',
                           '[p]olkit-kde-authentication-agent-1|[h]yprpolkitagent'])
            if agent.returncode == 0:
                report(True, 'Authentication agent already running outside hyprixe-polkit.service')
                continue
        detail = f'{unit}: {state.get("ActiveState", "unavailable")}'
        if state.get('Result'):
            detail += f' (result={state["Result"]})'
        if not running:
            detail += f'; inspect journalctl --user -b -u {unit}'
        report(running, detail)
        ok = ok and running
    wallpaper = states['hyprixe-wallpaper.service']
    for unit in ('waybar.service', 'swaync.service'):
        state = states[unit]
        ordered = ('hyprixe-wallpaper.service' in state.get('After', '').split() and
                   'hyprixe-wallpaper.service' in state.get('Wants', '').split())
        report(ordered, f'{unit}: pulls in and starts after the wallpaper service' if ordered else
               f'{unit}: wallpaper ordering is missing from loaded units; reinstall, log out and log in again')
        ok = ok and ordered
        try:
            start = int(state.get('InactiveExitTimestampMonotonic', 0))
            wp_start = int(wallpaper.get('InactiveExitTimestampMonotonic', 0))
            wp_ready = int(wallpaper.get('ActiveEnterTimestampMonotonic', 0))
        except ValueError:
            start = wp_start = wp_ready = 0
        if not start or not wp_start or not wp_ready:
            print(f'SKIPPED: {unit} startup chronology (active timestamps unavailable)')
        elif wp_start > start:
            print(f'SKIPPED: {unit} initial chronology (wallpaper was restarted later)')
        else:
            ordered_time = wp_ready <= start
            report(ordered_time, f'{unit}: wallpaper request completed before service activation' if ordered_time else
                   f'{unit}: activated before wallpaper completion; inspect monotonic user journal timestamps')
            ok = ok and ordered_time
    return ok
