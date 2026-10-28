"""Repository checks; missing optional validators and real-session tests say SKIPPED."""
import argparse
import ast
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from waybar_compat import has_lua_workspace_ipc, has_wlr_taskbar
from waybar_checks import check_source as check_waybar_source, check_installed as check_waybar_installed
from rofi_compat import has_wayland_support
from session_checks import check_session, check_source_order
from keybind_checks import check_native_config, check_session_keybinds
from terminal_checks import check_source as check_terminal_source, check_installed as check_terminal_installed
from wlogout_checks import check_source as check_wlogout_source, check_installed as check_wlogout_installed
from sddm_theme import SystemTheme, source_payload as sddm_payload, FILES as SDDM_FILES, THEME as SDDM_THEME
from session_diagnostics import collect as collect_session_diagnostics
from dolphin_checks import check_source as check_dolphin_source, check_installed as check_dolphin_installed, check_runtime as check_dolphin_runtime, check_session as check_dolphin_session

ROOT = Path(__file__).resolve().parents[1]
failed = 0


def report(ok, message):
    global failed
    print(('PASS: ' if ok else 'FAIL: ') + message, flush=True)
    if not ok:
        failed += 1


def run(command, message, **kwargs):
    try:
        r = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, **kwargs)
    except OSError as exc:
        r = subprocess.CompletedProcess(command, 127, '', str(exc))
    report(r.returncode == 0, message)
    if r.returncode:
        print(r.stdout + r.stderr)
    return r


def check_configuration_formats(root):
    # Check the files actually used by the launchers, not a legacy Waybar
    # include wrapper. Report each missing/invalid file and keep checking.
    formats = (
        ('.config/hypr/waybar/configs/Frosted-Glass', 'Waybar JSON', json.loads),
        ('.config/Kvantum/Frosted-Glass/Frosted-Glass.svg', 'Kvantum SVG', ET.fromstring),
        ('.local/share/kxmlgui5/dolphin/dolphinui.rc', 'Dolphin XML', ET.fromstring),
    )
    for relative, label, parse in formats:
        try:
            parse((root / relative).read_text(encoding='utf-8'))
        except (OSError, ValueError, ET.ParseError) as exc:
            report(False, f'{label}: {relative}: {exc}')
        else:
            report(True, f'{label}: {relative} parses')


def check_source_tree(root, entries):
    broken = [p for p in entries if p.is_symlink() and not p.exists()]
    for path in broken:
        report(False, f'Broken source symlink: {path.relative_to(root)} -> {os.readlink(path)!r}')
    required = ('configs/Frosted-Glass', 'style.css', 'style/Frosted-Glass.css')
    missing = [root / '.config/hypr/waybar' / name for name in required
               if not (root / '.config/hypr/waybar' / name).is_file()]
    for path in missing:
        report(False, f'Required Waybar source file missing: {path.relative_to(root)}')
    if not broken and not missing:
        report(True, 'Source files: no broken symlinks; active Waybar JSON and CSS exist')
    return not broken and not missing


def check_original_assets(root):
    try:
        lines = (root / 'docs/inventory-original.tsv').read_text().splitlines()[1:]
        manifest = {line.split('\t')[0]: line.split('\t')[2] for line in lines}
    except (OSError, UnicodeError, IndexError) as exc:
        report(False, f'Cannot read original asset inventory: {exc}')
        return
    assets = ('wallpapers/min_forest.jpg',
              '.config/Kvantum/Frosted-Glass/Frosted-Glass.svg',
              '.config/Kvantum/Frosted-Glass/Frosted-Glass.kvconfig')
    for name in assets:
        try:
            expected = manifest[name]
            actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        except (OSError, KeyError) as exc:
            report(False, f'Original asset: {name}: {exc}')
            continue
        detail = '' if actual == expected else f' (expected {expected}, got {actual})'
        report(actual == expected, f'Original asset SHA256: {name}{detail}')


def check_sddm(root, installed=False):
    try:
        sddm_payload(root)
        theme = root / 'sddm/themes' / SDDM_THEME
        metadata = configparser.ConfigParser(interpolation=None)
        metadata.read(theme / 'metadata.desktop')
        settings = configparser.ConfigParser(interpolation=None)
        settings.read(theme / 'theme.conf')
        assert metadata['SddmGreeterTheme']['QtVersion'] == '6'
        assert metadata['SddmGreeterTheme']['MainScript'] == 'Main.qml'
        assert settings['General']['background'] == 'min_forest.jpg'
    except (OSError, ValueError, KeyError, AssertionError, configparser.Error) as exc:
        report(False, f'SDDM theme source/metadata/wallpaper: {exc}')
        return
    report(True, 'SDDM Qt 6 theme, QML components, icon and original wallpaper exist; no forced virtual keyboard')
    lint = '/usr/lib/qt6/bin/qmllint' if Path('/usr/lib/qt6/bin/qmllint').is_file() else shutil.which('qmllint6')
    if not lint and shutil.which('qmllint'):
        version = subprocess.run(['qmllint', '--version'], capture_output=True, text=True)
        if version.returncode == 0 and re.search(r'\b6\.\d', version.stdout + version.stderr):
            lint = shutil.which('qmllint')
    if lint:
        # SDDM injects config/sddm/userModel/sessionModel at runtime; qmllint
        # cannot resolve those context globals. Keep their notices as info;
        # syntax, imports, missing properties and other warnings still fail.
        run([lint, '--ignore-settings', '--unqualified', 'info',
             *[str(theme / name) for name in SDDM_FILES if name.endswith('.qml')]],
            'Qt 6 qmllint: SDDM theme (runtime context globals reported as info)')
    else:
        print('SKIPPED: Qt 6 qmllint unavailable (optional: qt6-declarative-dev-tools)')
    if installed:
        try:
            failures = SystemTheme(repo=root).check_installed()
        except (OSError, ValueError, configparser.Error) as exc:
            failures = [str(exc)]
        report(not failures, 'Installed SDDM files, effective theme, disabled InputMethod and UWSM session entry' +
               (': ' + '; '.join(failures) if failures else ''))
        run(['python3', 'scripts/sddm_theme.py', 'prerequisites'], 'Installed SDDM Qt 6 greeter and QML dependencies')
    else:
        print('SKIPPED: system SDDM installation (use --sddm or --dependencies on target)')


def check_taskbar(root):
    try:
        bar = json.loads((root / '.config/hypr/waybar/configs/Frosted-Glass').read_text())
        taskbar = bar['wlr/taskbar']
        left = bar['modules-left']
        assert left.count('wlr/taskbar') == 1 and left.index('wlr/taskbar') == left.index('hyprland/workspaces') + 1
        assert taskbar['format'] == '{icon}' and taskbar['on-click'] == 'activate'
        assert taskbar['all-outputs'] is True and taskbar['tooltip-format'] == '{title}'
        css = (root / '.config/hypr/waybar/style/Frosted-Glass.css').read_text()
        assert '#taskbar button.active' in css
    except (OSError, ValueError, KeyError, TypeError, AttributeError, AssertionError) as exc:
        report(False, f'Waybar icon taskbar configuration/style: {exc or "missing icon/focus/active-state setting"}')
    else:
        report(True, 'Waybar taskbar: icons beside workspaces, focus click, per-window tooltips and active style')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', action='store_true', help='Also query an existing Hyprland session (read-only)')
    parser.add_argument('--dependencies', action='store_true', help='Require installed runtime dependencies')
    parser.add_argument('--sddm', action='store_true', help='Also check installed SDDM theme, configuration and UWSM entry')
    parser.add_argument('--diagnostics', action='store_true', help='Print read-only login journals, service timings, clients, layers and autostarts')
    parser.add_argument('--dolphin', action='store_true', help='Check only Dolphin source, deployed paint and Qt/Kvantum runtime')
    parser.add_argument('--waybar', action='store_true', help='Check only Waybar source and installed layout/runtime')
    args = parser.parse_args()
    if args.waybar:
        if args.dolphin or args.sddm or args.diagnostics:
            parser.error('--waybar cannot check another component')
        check_waybar_source(report, ROOT)
        check_taskbar(ROOT)
        check_waybar_installed(report)
        if args.session:
            check_session(report)
        print(f'RESULT: {failed} failed check(s)')
        return 1 if failed else 0
    if args.dolphin:
        if args.sddm or args.diagnostics:
            parser.error('--dolphin is a component-only check; run session/SDDM/diagnostic checks separately')
        check_dolphin_source(report, ROOT)
        check_dolphin_installed(report)
        check_dolphin_runtime(report)
        if args.session:
            check_session(report)
            check_dolphin_session(report)
        print(f'RESULT: {failed} failed check(s)')
        return 1 if failed else 0
    entries = [p for p in ROOT.rglob('*') if not any(x in p.relative_to(ROOT).parts for x in ('.git', '.validation', '__pycache__'))]
    sources_ok = check_source_tree(ROOT, entries)
    files = [p for p in entries if p.is_file()]
    shells = sorted(p for p in files if p.suffix == '.sh')
    shell_results = [subprocess.run(['bash', '-n', str(p)], capture_output=True, text=True) for p in shells]
    report(all(r.returncode == 0 for r in shell_results), f'bash -n: {len(shells)} scripts (including optional examples)')
    for p, r in zip(shells, shell_results):
        if r.returncode: print(p.relative_to(ROOT), r.stderr)
    if shutil.which('shellcheck'):
        run(['shellcheck', '-S', 'error', '-f', 'gcc', *map(str, shells)], 'ShellCheck: all scripts, severity error')
        active = [p for p in shells if 'extras' not in p.relative_to(ROOT).parts]
        run(['shellcheck', '-S', 'warning', '-f', 'gcc', *map(str, active)], 'ShellCheck: active scripts, severity warning')
    else:
        print('SKIPPED: ShellCheck unavailable')
    luas = sorted(p for p in files if p.suffix == '.lua')
    if shutil.which('luac'):
        results = [subprocess.run(['luac', '-p', str(p)], capture_output=True, text=True) for p in luas]
        report(all(r.returncode == 0 for r in results), f'luac -p: {len(luas)} Lua files')
        for p, r in zip(luas, results):
            if r.returncode: print(p.relative_to(ROOT), r.stderr)
        env = dict(os.environ, XDG_CONFIG_HOME=str(ROOT / '.config'))
        run(['lua', 'tests/check_lua.lua', str(ROOT / '.config')], 'Lua loading / required shortcuts / duplicate chords (mock)', env=env)
    else:
        print('SKIPPED: Lua compiler and load test unavailable')
    check_native_config(report, ROOT)
    for p in files:
        if p.suffix == '.py' or p == ROOT / '.local/bin/hyprixe-session':
            try: ast.parse(p.read_text(), str(p))
            except SyntaxError as exc: report(False, str(exc))
    report(True, 'Python syntax parsed without generating bytecode')
    if sources_ok:
        tests = run(['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], 'Deployment and runtime integration tests (isolated temporary HOME / mocked commands)')
        if tests.returncode == 0:
            for line in tests.stderr.splitlines():
                if line.startswith('Ran ') or line.startswith('OK'): print(line)
                elif ' ... skipped ' in line: print('SKIPPED: ' + line)
    else:
        print('SKIPPED: integration tests require intact source files; repair the source failures reported above first')
    active_files = [p for p in files if p.relative_to(ROOT).parts[0] in ('.config', '.local') or p.is_relative_to(ROOT / 'profiles/native')]
    forbidden = re.compile(r'VMware|vmwgfx|llvmpipe|Virtual-1|LIBGL_ALWAYS_SOFTWARE|MESA_LOADER_DRIVER_OVERRIDE|GALLIUM_DRIVER|WLR_RENDERER_ALLOW_SOFTWARE|/home/luc|Tokyo|\balacritty\b|\bthunar\b', re.I)
    hits = []
    for p in active_files:
        try:
            if forbidden.search(p.read_text()): hits.append(str(p.relative_to(ROOT)))
        except UnicodeError: pass
    report(not hits, 'Native tree: no graphics workarounds, machine paths or obsolete app/theme defaults' + (': ' + ', '.join(hits) if hits else ''))
    config = ROOT / '.config/hypr'
    entry = (config / 'hyprland.lua').read_text()
    modules = re.findall(r'"((?:lua|UserConfigs)/[^"\n]+\.lua|profile\.lua)"', entry)
    missing = [x for x in modules if not (config / x).is_file()]
    for p in (config / 'rofi').rglob('*.rasi'):
        for name in re.findall(r'@(?:import|theme)\s+"([^"]+)"', p.read_text()):
            if not (p.parent / name).is_file(): missing.append(f'{p.name}: {name}')
    scripts = set(re.findall(r'(?:script\(|scripts\s*\.\.\s*)"([A-Za-z][\w-]+\.sh)', (config / 'lua/keybinds.lua').read_text() + (config / 'lua/startup.lua').read_text()))
    for name in scripts:
        if not (config / 'scripts' / name).is_file(): missing.append(name)
    report(not missing, 'Entry modules, keybind scripts and Rofi theme imports resolve' + (': ' + ', '.join(missing) if missing else ''))
    check_configuration_formats(ROOT)
    check_terminal_source(report, ROOT)
    check_wlogout_source(report, ROOT)
    check_dolphin_source(report, ROOT)
    check_taskbar(ROOT)
    check_waybar_source(report, ROOT)
    check_sddm(ROOT, installed=args.sddm or args.dependencies)
    ordering = check_source_order(ROOT / '.config/systemd/user')
    report(not ordering, 'UWSM service ordering: wallpaper before Waybar/notifications' +
           (': ' + '; '.join(ordering) if ordering else ''))
    if args.dependencies:
        settings = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        ordering = check_source_order(settings / 'systemd/user')
        report(not ordering, 'Installed Hyprixe wallpaper/session units and vendor drop-ins' +
               (': ' + '; '.join(ordering) if ordering else ''))
    rofi = shutil.which('rofi')
    if rofi and has_wayland_support(rofi):
        for p in sorted((config / 'rofi').rglob('*.rasi')):
            # Rofi 2.0.0's early -rasi-validate path segfaults upstream, including
            # on minimal themes. -dump-theme uses the fully initialized parser
            # and exits before opening a graphical window.
            run([rofi, '-config', str(p), '-dump-theme'], 'Rofi parser: ' + str(p.relative_to(config)))
    elif rofi:
        report(False, f'Rofi lacks Wayland support: {rofi}; run ./install.sh native')
        print('SKIPPED: theme parser requires a suitable Wayland Rofi; this is a runtime capability failure, not six theme failures')
    else:
        print('SKIPPED: real Rofi theme parser unavailable')
    if shutil.which('waybar'):
        report(has_lua_workspace_ipc(), 'Waybar supports Lua workspace IPC required by this configuration')
        report(has_wlr_taskbar(), 'Waybar includes native wlr/taskbar and foreign-toplevel support')
    else:
        print('SKIPPED: Waybar Lua IPC capability check (binary unavailable)')
    check_original_assets(ROOT)
    secrets = re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:OPENSSH|RSA|EC|DSA) PRIVATE KEY|AKIA[0-9A-Z]{16}')
    secret_files = []
    for p in files:
        try:
            if secrets.search(p.read_text()): secret_files.append(str(p.relative_to(ROOT)))
        except UnicodeError: pass
    report(not secret_files, 'Secret-pattern scan (current files): ' + (', '.join(secret_files) if secret_files else 'no matches'))
    if shutil.which('git'):
        executable_paths = ['install.sh', 'uninstall.sh', 'verify.sh', 'scripts/build-runtime.sh', '.local/bin/hyprixe-session']
        executable_paths += [str(p.relative_to(ROOT)) for p in (config / 'scripts').glob('*.sh')]
        executable_paths += [str(p.relative_to(ROOT)) for p in (config / 'UserScripts').glob('*.sh')]
        waybar_css = '.config/hypr/waybar/style.css'
        index = subprocess.run(['git', 'ls-files', '-s', '--', *executable_paths, waybar_css], cwd=ROOT, capture_output=True, text=True)
        modes = {line.split('\t', 1)[1]: line.split()[0] for line in index.stdout.splitlines()}
        report(index.returncode == 0 and all(modes.get(name) == '100755' for name in executable_paths), 'Executable entrypoints and active scripts recorded as 100755 in Git')
        report(index.returncode == 0 and modes.get(waybar_css) == '100644', 'Waybar style.css recorded as a regular file in Git (not a CSS-text symlink)')
    if args.dependencies:
        run(['python3', 'scripts/check-deps.py'], 'Installed runtime dependencies')
        check_terminal_installed(report)
        check_wlogout_installed(report, ROOT)
        check_waybar_installed(report)
        check_dolphin_installed(report)
        check_dolphin_runtime(report)
    else:
        print('SKIPPED: installed graphical dependencies (use --dependencies on target)')
    if args.session:
        if not args.dependencies:
            check_terminal_installed(report)
            check_wlogout_installed(report, ROOT)
        check_session(report)
        check_dolphin_session(report)
        check_session_keybinds(report, ROOT)
        if shutil.which('hyprctl') and os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
            run(['hyprctl', 'monitors', '-j'], 'hyprctl monitors')
            run(['awww', 'query'], 'awww query')
        else:
            print('SKIPPED: compositor IPC checks require hyprctl and a current Hyprland environment')
    else:
        print('SKIPPED: UWSM/session services, hyprctl configerrors, outputs and wallpaper IPC (use --session inside Hyprland)')
    if args.diagnostics:
        collect_session_diagnostics()
    print('SKIPPED: visual theme, keyboard/mouse actions, PAM unlock and suspend/resume require interactive hardware testing')
    print(f'RESULT: {failed} failed check(s)')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
