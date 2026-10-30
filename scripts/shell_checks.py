"""Interactive shell checks without opening Kitty or changing accounts."""
import os
import json
from pathlib import Path
import pwd
import re
import shutil
import subprocess

import interactive_shell
import shell_assets

KITTY_SHELL_PROBE = '''import json,sys
from kitty.config import load_config
from kitty.utils import resolved_shell
print(json.dumps(resolved_shell(load_config(sys.argv[1]))))
'''


def check_source(report, root):
    files = [Path(root) / name for name in ('.zshrc', '.p10k.zsh')]
    try:
        rc, prompt = [path.read_text() for path in files]
        if '/home/' in rc + prompt or re.search(r'^\s*shell\s+(?!\.\s*$)', (Path(root) / '.config/kitty/kitty.conf').read_text(), re.M):
            raise ValueError('Shell paths must be portable and Kitty must use the account shell')
        first = rc.index('p10k-instant-prompt-')
        if first > rc.index('compinit') or not rc.strip().endswith('source ' + interactive_shell.PLUGINS[-1]):
            raise ValueError('Instant Prompt/highlighting startup order is incorrect')
        for name in interactive_shell.PLUGINS:
            if 'source ' + name not in rc:
                raise ValueError('Missing direct Debian plugin source: ' + name)
        if 'POWERLEVEL9K_DISABLE_CONFIGURATION_WIZARD=true' not in prompt:
            raise ValueError('Hyprixe must provide a ready-to-use P10k configuration')
        for path in files:
            if shutil.which('zsh'):
                result = subprocess.run(['zsh', '-n', str(path)], capture_output=True, text=True, timeout=15)
                if result.returncode:
                    raise ValueError(result.stderr.strip())
        report(True, 'Zsh source: portable config, native completion/history, Instant Prompt and Debian plugins in order')
        if not shutil.which('zsh'):
            print('SKIPPED: native zsh -n parser unavailable')
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        report(False, 'Zsh source: ' + str(exc))


def check_installed(report):
    home = Path.home()
    roots = {key: Path(os.environ.get(env, home / default)) for key, env, default in (
        ('config', 'XDG_CONFIG_HOME', '.config'), ('data', 'XDG_DATA_HOME', '.local/share'),
        ('state', 'XDG_STATE_HOME', '.local/state'))}
    try:
        errors = interactive_shell.dependencies()
        if errors:
            raise ValueError('; '.join(errors))
        user = pwd.getpwuid(os.getuid())
        binary = shutil.which('zsh')
        if not interactive_shell.allowed_shell(user.pw_shell) or Path(user.pw_shell).resolve() != Path(binary).resolve():
            raise ValueError('Account login shell is not Zsh; complete ./install.sh native and reconnect')
        for name in ('.zshrc', '.p10k.zsh'):
            if not (home / name).is_file():
                raise ValueError('Installed shell configuration missing: ' + name)
        shell_assets.validate(roots['data'] / 'hyprixe/powerlevel10k')
        shell_assets.check_daemon(roots['data'] / 'hyprixe/powerlevel10k')
        font = roots['data'] / 'fonts/hyprixe-symbols' / shell_assets.FONT
        if shell_assets.sha(font.read_bytes()) != shell_assets.PINS['symbols']['sha256']:
            raise ValueError('Installed Nerd Font does not match the pinned font')
        kitty = (roots['config'] / 'kitty/kitty.conf').read_text()
        if re.search(r'^\s*shell\s+(?!\.\s*$)', kitty, re.M):
            raise ValueError('Kitty must use its default account shell')
        selected = subprocess.run(['kitty', '+runpy', KITTY_SHELL_PROBE, str(roots['config'] / 'kitty/kitty.conf')],
                                  capture_output=True, text=True, timeout=15)
        command = json.loads(selected.stdout) if selected.returncode == 0 else []
        if selected.stderr.strip() or len(command) != 1 or Path(command[0]).resolve() != Path(user.pw_shell).resolve():
            raise ValueError('Kitty still resolves another shell in this environment; reconnect the desktop session to refresh SHELL')
        interactive_shell.font_ready()
        interactive_shell.startup(home, roots)
        report(True, 'Installed Zsh: account shell, pinned Powerlevel10k/gitstatus, Nerd symbols, plugins and silent zsh -lic startup')
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        report(False, 'Installed interactive shell: ' + str(exc))
