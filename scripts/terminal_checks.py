"""Kitty migration checks, including its real parser without starting a window."""
import configparser
import os
from pathlib import Path
import re
import shutil
import subprocess

# Run with Kitty's bundled Python: no extra Python module or display is needed.
# Kitty logs unknown options instead of adding them to accumulate_bad_lines;
# stderr is therefore checked as well as exceptions and collected parse errors.
PARSER = '''import sys
from kitty.config import load_config
errors = []
load_config(sys.argv[1], accumulate_bad_lines=errors)
for error in errors:
    print(str(error), file=sys.stderr)
sys.exit(bool(errors))
'''


def config_errors(path):
    path = Path(path)
    if not path.is_file():
        return [f'Kitty configuration missing: {path}']
    binary = shutil.which('kitty')
    if not binary:
        return ['Kitty parser unavailable: install the Debian kitty package']
    try:
        result = subprocess.run([binary, '+runpy', PARSER, str(path)],
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f'Kitty parser: {exc}']
    if result.returncode or result.stderr.strip():
        return [f'Kitty parser: {path}: {(result.stderr or result.stdout).strip() or result.returncode}']
    return []


def check_config(report, path):
    path = Path(path)
    report(path.is_file(), f'Kitty configuration exists: {path}')
    if not path.is_file():
        return
    if not shutil.which('kitty'):
        print('SKIPPED: native Kitty parser unavailable (install the Debian kitty package)')
        return
    errors = config_errors(path)
    report(not errors, 'Kitty native configuration parser (no window/display): ' +
           ('; '.join(errors) if errors else 'accepted'))


def runtime_errors():
    errors = []
    if not shutil.which('kitty'):
        errors.append('Kitty executable missing; install the Debian kitty package')
    if not shutil.which('fc-match'):
        return errors + ['fontconfig (fc-match) is required to check the terminal font']
    try:
        result = subprocess.run(['fc-match', '-f', '%{family}', 'JetBrains Mono'],
                                capture_output=True, text=True, timeout=15)
        if result.returncode or 'JetBrains Mono' not in result.stdout.split(','):
            errors.append('JetBrains Mono font missing; install fonts-jetbrains-mono')
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(f'Terminal font check: {exc}')
    return errors


def integration_errors(config):
    """Check active defaults without touching old personal Alacritty files."""
    config = Path(config)
    checks = {
        'hypr/UserConfigs/user_defaults.lua': r'\bterm\s*=\s*"kitty"',
        'hypr/scripts/LaunchTerminal.sh': r'exec uwsm app -- kitty "\$@"',
        'hypr/rofi/config.rasi': r'terminal:\s*"kitty";',
        'hypr/lua/keybinds.lua': r'bind\("SUPER \+ Return", script\("LaunchTerminal.sh"\), \{ description = "Kitty" \}\)',
    }
    errors = []
    for name, pattern in checks.items():
        try:
            text = (config / name).read_text()
            if not re.search(pattern, text) or re.search(r'\balacritty\b', text, re.I):
                errors.append(f'Stale terminal integration: {name}; reinstall and log in again')
        except OSError as exc:
            errors.append(f'Terminal integration: {name}: {exc}')
    try:
        kde = configparser.ConfigParser(interpolation=None)
        kde.read(config / 'kdeglobals')
        if (kde.get('General', 'TerminalApplication', fallback='') != 'kitty' or
                kde.get('General', 'TerminalService', fallback='') != 'kitty.desktop'):
            errors.append('KDE terminal default must be kitty / kitty.desktop')
    except configparser.Error as exc:
        errors.append(f'KDE terminal defaults: {exc}')
    return errors


def check_source(report, root):
    root = Path(root)
    errors = integration_errors(root / '.config')
    report(not errors, 'Kitty defaults: SUPER + Return, UWSM launcher, Rofi and KDE' +
           (': ' + '; '.join(errors) if errors else ' agree'))
    report(not (root / '.config/alacritty').exists(), 'No active Alacritty configuration is shipped')
    check_config(report, root / '.config/kitty/kitty.conf')


def check_installed(report):
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    errors = integration_errors(config)
    report(not errors, 'Installed Kitty terminal integration' +
           (': ' + '; '.join(errors) if errors else ': consistent'))
    check_config(report, config / 'kitty/kitty.conf')
