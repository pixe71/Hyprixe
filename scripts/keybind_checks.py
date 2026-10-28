"""Audit the actual Lua registry without executing a user's window actions.

Hyprland 0.55.2/0.56.2 exports __lua callbacks, not their bodies, in binds JSON.
Lua keycode binds also have key='' and keycode=0 there. Descriptions identify
our rows; retained HL.Keybind handles provide display_key and enabled state.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

PREFIX = 'Hyprixe | '
MODIFIERS = {'SHIFT': 1, 'CTRL': 4, 'ALT': 8, 'SUPER': 64}


@dataclass(frozen=True)
class Binding:
    chord: str
    repeating: bool = False
    locked: bool = False

    @property
    def mask(self):
        return sum(MODIFIERS[x] for x in self.chord.split(' + ')[:-1])

    @property
    def key(self):
        return self.chord.split(' + ')[-1]


def expected_bindings():
    """Independent contract for all shipped shortcuts, including physical keys."""
    result = [Binding('SUPER + ' + key) for key in
              ('Return', 'Backspace', 'E', 'Space', 'Q', 'L', 'F', 'SHIFT + F', 'V', 'P', 'J',
               'mouse:272', 'mouse:273')]
    for direction in ('left', 'right', 'up', 'down'):
        result += [Binding('SUPER + ' + direction), Binding('SUPER + SHIFT + ' + direction),
                   Binding('SUPER + CTRL + ' + direction, repeating=True)]
    for code in range(10, 20):
        result += [Binding(f'SUPER + code:{code}'), Binding(f'SUPER + SHIFT + code:{code}')]
    result += [Binding('SUPER + ' + key) for key in ('mouse_down', 'mouse_up', 'Page_Down', 'Page_Up')]
    result += [Binding(chord) for chord in ('ALT + Tab', 'ALT + SHIFT + Tab', 'ALT + F10',
               'SUPER + SHIFT + E', 'SUPER + CTRL + V', 'SUPER + SHIFT + S', 'Print',
               'SHIFT + Print', 'SUPER + Print', 'SUPER + SHIFT + Print')]
    result += [Binding(key, locked=True, repeating=key in ('XF86AudioRaiseVolume', 'XF86AudioLowerVolume'))
               for key in ('XF86AudioRaiseVolume', 'XF86AudioLowerVolume', 'XF86AudioMute',
                           'XF86AudioMicMute', 'XF86AudioPlay', 'XF86AudioNext', 'XF86AudioPrev')]
    result += [Binding(key, repeating=True) for key in ('XF86MonBrightnessUp', 'XF86MonBrightnessDown')]
    return result


EXPECTED = expected_bindings()
SCRIPTS = ('LaunchTerminal.sh', 'LaunchApp.sh', 'RofiLauncher.sh', 'LockScreen.sh',
           'WindowSwitcher.sh', 'PowerMenu.sh', 'ClipManager.sh', 'ScreenShot.sh')
COMMANDS = ('hyprctl', 'jq', 'rofi', 'uwsm', 'kitty', 'dolphin', 'hyprlock', 'wlogout', 'hyprixe-session',
            'flock', 'pgrep', 'cliphist', 'wl-copy', 'grim', 'slurp', 'wpctl',
            'playerctl', 'brightnessctl', 'systemctl', 'xdg-user-dir', 'notify-send')


def managed_chord(row):
    description = row.get('description', '')
    return description[len(PREFIX):].split(' | ', 1)[0] if description.startswith(PREFIX) else None


def registry_errors(rows):
    """Compare actual rows, then detect duplicate triggers including user binds.

Disabled state is deliberately NOT inferred here: JSON does not export it.
The companion handle probe must pass too. Unknown code rows cannot be proved
conflict-free and are reported rather than silently accepted.
"""
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return ['hyprctl binds must return a JSON array of objects']
    errors, by_chord, triggers = [], {}, {}
    for row in rows:
        chord = managed_chord(row)
        if chord:
            by_chord.setdefault(chord, []).append(row)
        key = str(row.get('key', '')).lower()
        if not key and row.get('keycode'):
            key = 'code:' + str(row['keycode'])
        if not key and chord:
            key = chord.split(' + ')[-1].lower()
        if not key:
            errors.append('Opaque unlabelled bind: JSON omits its physical key; inspect hyprctl binds and personal overrides')
            continue
        try:
            mask = int(row.get('modmask', -1))
        except (ValueError, TypeError):
            errors.append(f'Invalid modifier mask for {chord or key}')
            continue
        trigger = (row.get('submap', ''), mask, key, bool(row.get('release')), bool(row.get('longPress')))
        triggers.setdefault(trigger, []).append(chord or row.get('description') or key)
    for trigger, labels in triggers.items():
        if len(labels) > 1:
            errors.append(f'Duplicate/conflicting trigger {trigger}: {", ".join(labels)}')
    for spec in EXPECTED:
        matches = by_chord.get(spec.chord, [])
        if len(matches) != 1:
            errors.append(f'{spec.chord}: expected one loaded Hyprixe bind, found {len(matches)}; install and reload the updated config')
            continue
        row = matches[0]
        conditions = {
            'modmask': spec.mask, 'submap': '', 'dispatcher': '__lua',
            'repeat': spec.repeating, 'locked': spec.locked, 'release': False,
            'mouse': False, 'non_consuming': False, 'catch_all': False,
        }
        for name, value in conditions.items():
            if row.get(name) != value:
                errors.append(f'{spec.chord}: {name}={row.get(name)!r}, expected {value!r}')
        key = str(row.get('key', ''))
        if spec.key.startswith('code:'):
            # Both empty fields are the upstream Lua JSON representation.
            if (key not in ('', spec.key) or row.get('keycode', 0) not in (0, int(spec.key[5:]))):
                errors.append(f'{spec.chord}: wrong physical key in registry')
        elif key.lower() != spec.key.lower():
            errors.append(f'{spec.chord}: unexpected key {key!r}')
        if not re.fullmatch(r'[1-9][0-9]*', str(row.get('arg', ''))):
            errors.append(f'{spec.chord}: invalid/removed Lua callback reference')
    unknown = set(by_chord) - {b.chord for b in EXPECTED}
    if unknown:
        errors.append('Unexpected managed binds: ' + ', '.join(sorted(unknown)))
    return errors


def handle_probe():
    """Read retained real HL.Keybind objects, including later disable/unbind."""
    expected = ','.join(f'[{json.dumps(spec.chord)}]={spec.mask}' for spec in EXPECTED)
    return '''assert(KOOLDOTS_DEFAULTS and KOOLDOTS_DEFAULTS.term == 'kitty', 'Terminal default is not Kitty; reinstall and log in again')
assert(os.getenv('TERMINAL') == 'kitty', 'Compositor TERMINAL is not kitty; log in again')
assert(HYPRIXE_KEYBINDS_REVISION == 1, 'Old/missing Hyprixe keybind audit metadata; reinstall and reload')
assert(type(KOOLDOTS_BINDS) == 'table', 'KOOLDOTS_BINDS is not loaded')
for chord, mask in pairs({''' + expected + '''}) do
local b = assert(KOOLDOTS_BINDS[chord], 'Missing ' .. chord)
-- Upstream 0.55.2 can dereference an expired handle in property getters.
-- __tostring checks the weak pointer safely; do this BEFORE any field/method.
assert(tostring(b) ~= 'HL.Keybind(expired)', 'Disabled/removed ' .. chord)
assert(b:is_enabled() == true, 'Disabled/removed ' .. chord)
assert(b.display_key == chord and b.modmask == mask and b.submap == '', 'Wrong trigger/submap ' .. chord)
assert(not b.ignore_mods and not b.transparent and not b.non_consuming and not b.auto_consuming
 and not b.click and not b.drag and not b.submap_universal and not b.long_press
 and not b.dont_inhibit and not b.device_inclusive and #b.devices == 0, 'Unexpected flags/device filter ' .. chord)
local identity = 'Hyprixe | ' .. chord
assert(b.description and (b.description == identity or b.description:sub(1, #identity+3) == identity .. ' | '), 'Changed identity ' .. chord)
if chord == 'SUPER + Return' then
 assert(b.description == identity .. ' | Kitty', 'Stale terminal binding; reinstall and reload')
end
end'''


# Construct exactly the dispatcher variants used by these bindings, but execute
# ONLY no_op. Calling close/focus/resize/lock to test support would disturb users.
API_PROBE = '''(function()
local d, w = hl.dsp, hl.dsp.window
for _, name in ipairs({'get_windows','get_active_window','get_active_workspace','get_active_special_workspace'}) do
 assert(type(hl[name]) == 'function', 'Missing Lua query: '..name)
end
local actions = {d.exec_cmd('true'), w.close(), w.fullscreen({mode='fullscreen'}),
 w.fullscreen({mode='maximized'}), w.float({action='toggle'}), w.pseudo(),
 d.layout('togglesplit'), w.drag(), w.resize(), d.focus({window='address:0x1'}),
 w.alter_zorder({mode='top',window='address:0x1'})}
for _, dir in ipairs({'left','right','up','down'}) do
 actions[#actions+1] = d.focus({direction=dir})
 actions[#actions+1] = w.move({direction=dir})
end
for _, size in ipairs({{x=50,y=0},{x=-50,y=0},{x=0,y=50},{x=0,y=-50}}) do
 actions[#actions+1] = w.resize({x=size.x,y=size.y,relative=true})
end
for i=1,10 do actions[#actions+1]=d.focus({workspace=i}); actions[#actions+1]=w.move({workspace=i}) end
for _, ws in ipairs({'e+1','e-1'}) do actions[#actions+1]=d.focus({workspace=ws}) end
return d.no_op()
end)()'''


QUERY_PROBE = '''
local workspace = hl.get_active_special_workspace() or hl.get_active_workspace()
assert(workspace, 'No active workspace for window cycling')
local windows = hl.get_windows({workspace=workspace,mapped=true})
assert(type(windows) == 'table', 'get_windows did not return a snapshot')
for _, window in ipairs(windows) do
 assert(type(window.address) == 'string' and window.address:match('^0x%x+$'), 'Invalid window address')
 assert(type(window.stable_id) == 'number', 'Missing stable window ID')
 assert(type(window.hidden) == 'boolean' and type(window.accepts_input) == 'boolean', 'Missing window input/visibility properties')
end
'''


def check_native_config(report, root):
    """Use the installed compositor parser, isolated from the desktop session.

No backend, startup event, session IPC or user configuration is started/changed.
The native handle checks complement, rather than replace, the recording mock.
"""
    binary = shutil.which('Hyprland')
    if not binary:
        print('SKIPPED: real Hyprland --verify-config (binary unavailable)')
        return
    if os.geteuid() == 0:
        print('SKIPPED: real Hyprland --verify-config must run as an unprivileged desktop user')
        return
    try:
        with tempfile.TemporaryDirectory(prefix='hyprixe native API ') as folder:
            home = Path(folder)
            config = home / '.config/hypr'
            shutil.copytree(Path(root) / '.config/hypr', config)
            runtime = home / 'runtime'
            runtime.mkdir(mode=0o700)
            entry = config / 'hyprland.lua'
            with entry.open('a') as file:
                file.write('\n' + handle_probe() + '\nhl.dispatch(' + API_PROBE + ')\n')
            # Deliberately exclude the existing desktop's IPC/bus/display vars.
            env = {'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'),
                   'XDG_RUNTIME_DIR': str(runtime), 'XDG_DATA_HOME': str(home / 'data'),
                   'XDG_STATE_HOME': str(home / 'state'), 'LANG': 'C.UTF-8',
                   'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
            result = subprocess.run([binary, '--verify-config', '-c', str(entry)],
                                    env=env, capture_output=True, text=True, timeout=30)
            report(result.returncode == 0, f'Real Hyprland parser: isolated native config, {len(EXPECTED)} retained handles and dispatcher constructors')
            if result.returncode:
                print(result.stdout + result.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        report(False, 'Real Hyprland parser: ' + str(exc))


def check_session_keybinds(report, root, environ=None, runner=None, which=None):
    environ = os.environ if environ is None else environ
    runner = subprocess.run if runner is None else runner
    which = shutil.which if which is None else which
    if not environ.get('HYPRLAND_INSTANCE_SIGNATURE') or not which('hyprctl'):
        report(False, 'Live keybind audit requires hyprctl inside the current Hyprland session')
        return

    def query(*args):
        try:
            return runner(['hyprctl', *args], capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return subprocess.CompletedProcess(args, 1, '', str(exc))

    def ok_response(args, label):
        result = query(*args)
        ok = result.returncode == 0 and result.stdout.strip() == 'ok'
        report(ok, label + ('' if ok else ': ' + (result.stderr or result.stdout).strip()))

    version = query('version')
    match = re.search(r'\b0\.(55|56)\.(\d+)\b', version.stdout)
    supported = bool(match and (int(match[1]) == 56 or int(match[2]) >= 2))
    report(version.returncode == 0 and supported,
           'Live Hyprland API version (audited 0.55.2 / 0.56.x): ' + version.stdout.split('\n')[0])
    # Hyprland eval()/Lua dispatch clear the manager's stored errors upstream.
    # Never use them while existing configuration errors would be hidden.
    configerrors = query('configerrors')
    config_ok = configerrors.returncode == 0 and not configerrors.stdout.strip()
    report(config_ok, 'Running Hyprland reports no configuration errors' if config_ok else
           'Running Hyprland configuration errors (preserved; Lua probes skipped): ' +
           (configerrors.stderr or configerrors.stdout).strip())
    result = query('-j', 'binds')
    try:
        if result.returncode:
            raise ValueError(result.stderr or result.stdout)
        errors = registry_errors(json.loads(result.stdout))
        report(not errors, f'Actual Hyprland registry: {len(EXPECTED)} expected bindings, modifiers, flags and conflicts')
        for error in errors:
            print('  ' + error)
    except (ValueError, TypeError, AttributeError) as exc:
        report(False, 'Cannot read live keybind registry: ' + str(exc))
    prefix = str(Path(environ.get('HOME', Path.home())) / '.local/bin') + ':'
    environment_probe = ('\nassert((os.getenv("PATH") or ""):sub(1, ' + str(len(prefix)) + ') == ' +
                         json.dumps(prefix, ensure_ascii=False) + ', "Compositor PATH does not prioritize ~/.local/bin; log in again")')
    if config_ok:
        ok_response(('eval', handle_probe() + environment_probe + QUERY_PROBE),
                    'Actual Lua handles, enabled states, physical chords, device filters, compositor PATH and live window-query API')
        ok_response(('dispatch', API_PROBE), 'Native dispatcher constructors accepted; only no_op executed')
    else:
        print('SKIPPED: Lua handle/query/constructor probes preserve the existing compositor error state; fix configerrors first')
    submap = query('submap')
    report(submap.returncode == 0 and submap.stdout.strip() in ('', 'default'),
           'Current submap: ' + (submap.stdout.strip() or '(root)') + '; core shortcuts need the root/default submap')
    devices = query('-j', 'devices')
    try:
        if devices.returncode:
            raise ValueError(devices.stderr or devices.stdout)
        keyboards = json.loads(devices.stdout)['keyboards']
        report(bool(keyboards), 'Live keyboard devices/keymaps: ' + ', '.join(
            f'{k.get("name", "?")} [{k.get("active_keymap", "?")}]' for k in keyboards))
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        report(False, 'Cannot query live keyboard devices: ' + str(exc))
    home = Path(environ.get('HOME', Path.home()))
    config = Path(environ.get('XDG_CONFIG_HOME', home / '.config')) / 'hypr'
    missing = [str(config / 'scripts' / name) for name in SCRIPTS
               if not (config / 'scripts' / name).is_file() or not os.access(config / 'scripts' / name, os.X_OK)]
    report(not missing, 'Installed keybind scripts exist and are executable' + (': ' + ', '.join(missing) if missing else ''))
    drift = []
    for relative in ('hyprland.lua', 'lua/keybinds.lua', 'UserConfigs/user_defaults.lua', *('scripts/' + name for name in SCRIPTS)):
        try:
            if (config / relative).read_bytes() != (Path(root) / '.config/hypr' / relative).read_bytes():
                drift.append(relative)
        except OSError:
            drift.append(relative)
    report(not drift, 'Installed keybind files match this checkout' + (': reinstall before reloading: ' + ', '.join(drift) if drift else ''))
    missing_commands = [name for name in COMMANDS if not which(name)]
    report(not missing_commands, 'Keybind command dependencies' + (': missing ' + ', '.join(missing_commands) if missing_commands else ': available'))
    from rofi_compat import has_wayland_support
    rofi = which('rofi')
    report(bool(rofi) and has_wayland_support(rofi), 'Selected Rofi has Wayland support: ' + str(rofi))
    print('SKIPPED: input delivery, callback effects and focus behavior need physical key/mouse tests; registry/API checks do not simulate them')
