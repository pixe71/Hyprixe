"""Validate Zsh and transactionally change only the invoking desktop account."""
import os
from pathlib import Path
import pwd
import shutil
import subprocess

PLUGINS = ('/usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh',
           '/usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh')
PROBE = '''[[ -o interactive && -o login ]] || exit 21
(( $+functions[p10k] && $+functions[compdef] && $+functions[_zsh_autosuggest_start] && $+functions[_zsh_highlight] )) || exit 22
(( ${#POWERLEVEL9K_LEFT_PROMPT_ELEMENTS} )) || exit 23
[[ $HISTFILE == "${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe/zsh/history" ]] || exit 24
print -r -- HYPRIXE_ZSH_OK
'''


def dependencies():
    errors = []
    binary = shutil.which('zsh')
    if not binary:
        errors.append('Zsh missing; install the Debian zsh package')
    else:
        result = subprocess.run([binary, '--version'], capture_output=True, text=True, timeout=15)
        if result.returncode or not result.stdout.startswith('zsh '):
            errors.append('zsh --version failed')
    for name in PLUGINS:
        if not Path(name).is_file():
            errors.append('Debian Zsh plugin missing: ' + name)
    return errors


def startup(home, roots):
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(roots['config']),
               XDG_DATA_HOME=str(roots['data']), XDG_STATE_HOME=str(roots['state']), TERM='xterm-256color')
    result = subprocess.run([shutil.which('zsh') or '/usr/bin/zsh', '-lic', PROBE], env=env,
                            cwd=home, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
    if result.returncode or result.stdout.strip() != 'HYPRIXE_ZSH_OK' or result.stderr.strip():
        raise ValueError('Zsh startup failed; login shell unchanged. Check .zshenv/.zprofile/ZDOTDIR and plugins: ' +
                         (result.stderr or result.stdout or f'exit {result.returncode}').strip())


def font_ready():
    result = subprocess.run(['fc-match', '-f', '%{family}', 'Symbols Nerd Font Mono:charset=f306,f418,e73c'],
                            capture_output=True, text=True, timeout=15)
    if result.returncode or 'Symbols Nerd Font Mono' not in result.stdout.split(','):
        raise ValueError('The installed Nerd symbol font is not selected by fontconfig; check fc-cache/XDG_DATA_HOME')


def allowed_shell(path):
    allowed = [line.split('#', 1)[0].strip() for line in Path('/etc/shells').read_text().splitlines()]
    return bool(path and path in allowed and Path(path).is_file() and os.access(path, os.X_OK))


def plan(home):
    user = pwd.getpwuid(os.getuid())
    if user.pw_uid == 0 or Path(user.pw_dir).resolve() != home.resolve():
        raise ValueError('Login-shell migration requires the invoking non-root account and its real HOME')
    errors = dependencies()
    if errors:
        raise ValueError('; '.join(errors))
    binary = shutil.which('zsh')
    if not binary or not allowed_shell(str(Path(binary).resolve())):
        raise ValueError('The real Zsh executable must be executable and listed in /etc/shells')
    if not allowed_shell(user.pw_shell):
        raise ValueError('The original shell must be valid and listed in /etc/shells to support restoration')
    new = str(Path(binary).resolve())
    if Path(user.pw_shell).resolve() == Path(new):
        new = user.pw_shell
    return {'uid': user.pw_uid, 'username': user.pw_name, 'home': str(home),
            'before': user.pw_shell, 'after': new}


def preflight(record, home):
    user = pwd.getpwuid(os.getuid())
    if (user.pw_uid == 0 or record['uid'] != user.pw_uid or record['username'] != user.pw_name
            or record['home'] != str(home) or Path(user.pw_dir).resolve() != home.resolve()):
        raise ValueError('Login-shell backup belongs to a different account/HOME; nothing changed')
    if user.pw_shell not in (record['before'], record['after']):
        raise ValueError('Login shell changed since installation; save that change before restore')
    if not allowed_shell(record['before']):
        raise ValueError('Original login shell is no longer valid in /etc/shells')
    return user


def change(record, home, restore=False):
    user = preflight(record, home)
    target = record['before' if restore else 'after']
    if not allowed_shell(target):
        raise ValueError('Requested login shell is not valid in /etc/shells')
    if user.pw_shell == target:
        return
    binary = shutil.which('chsh', path='/usr/sbin:/usr/bin:/sbin:/bin')
    if not binary:
        raise ValueError('Debian chsh is unavailable; login shell unchanged')
    print(f'Changing login shell for {user.pw_name}: {user.pw_shell} -> {target}', flush=True)
    subprocess.run(['sudo', binary, '-s', target, user.pw_name], check=True)
    if pwd.getpwuid(user.pw_uid).pw_shell != target:
        raise ValueError('chsh did not set the requested login shell')
