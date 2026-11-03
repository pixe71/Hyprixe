"""Hyprixe's dark-first colour pipeline and single wallpaper transaction.

Only raw.json is a Wallust template (MiniJinja v3). Component templates use
Hyprixe @semantic_role@ tokens; they never consume numbered Wallust colours.
No package manager, session manager or distribution policy belongs here.
"""
import argparse
import colorsys
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid

WALLUST_VERSION = '3.5.1'
FILES = ('hyprland.lua', 'waybar.css', 'rofi.rasi', 'wlogout.css',
         'kitty.conf', 'hyprlock.conf', 'swaync.css')
HEX = re.compile(r'#[0-9a-fA-F]{6}\Z')
TOKEN = re.compile(r'@([a-z_]+)@')
OWNER = 'hyprixe-dynamic-theme-v1\n'
KITTY_PARSER = '''import sys
from kitty.config import load_config
errors = []
load_config(sys.argv[1], accumulate_bad_lines=errors)
for error in errors: print(str(error), file=sys.stderr)
sys.exit(bool(errors))
'''
GTK_PARSER = '''import sys, gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
provider = Gtk.CssProvider()
errors = []
provider.connect('parsing-error', lambda p, section, error: errors.append(str(error)))
provider.load_from_path(sys.argv[1])
for error in errors: print(error, file=sys.stderr)
sys.exit(bool(errors))
'''


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def rgb(color):
    if not isinstance(color, str) or not HEX.fullmatch(color):
        raise ValueError('Invalid RGB colour: ' + repr(color))
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def hexcolor(values):
    return '#' + ''.join(f'{round(max(0, min(1, v)) * 255):02x}' for v in values)


def luminance(color):
    values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb(color)]
    return sum(a * b for a, b in zip(values, (.2126, .7152, .0722)))


def contrast(a, b):
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


def readable(color, background, ratio):
    for _ in range(32):
        if contrast(color, background) >= ratio:
            return color
        color = hexcolor(v + (1 - v) * .08 for v in rgb(color))
    raise ValueError('Unable to preserve contrast')


def defaults(resources):
    return json.loads((resources / 'defaults/frosted-glass.json').read_text())


def normalize(raw, base):
    colors = raw['colors']
    if len(colors) != 16:
        raise ValueError('Wallust must return exactly 16 RGB colours')
    for color in [raw['background'], raw['foreground'], *colors]:
        rgb(color)
    # Pick chroma rather than a terminal index. Low-chroma images retain the
    # familiar cyan hue; fixed semantic status colours keep their meaning.
    candidates = [colorsys.rgb_to_hls(*rgb(c)) for c in colors]
    hue, _, saturation = max(candidates, key=lambda c: c[2] * (1 - abs(c[1] - .5)))
    if saturation < .12:
        hue = colorsys.rgb_to_hls(*rgb(base['accent']))[0]
    p = dict(base)
    for role, lightness, sat, offset in (
        ('background', .12, .30, 0), ('surface', .23, .26, 0),
        ('surface_alt', .28, .25, 0), ('accent', .75, .54, 0),
        ('accent_alt', .82, .38, .055), ('border', .46, .27, 0),
        ('border_focus', .53, .46, 0), ('border_secondary', .34, .40, 0),
        ('selection', .34, .28, 0), ('workspace', .46, .34, .22),
    ):
        p[role] = hexcolor(colorsys.hls_to_rgb((hue + offset) % 1, lightness, sat))
    for role in ('foreground', 'foreground_muted', 'accent', 'accent_alt', 'success', 'warning', 'error'):
        p[role] = readable(p[role], p['surface_alt'], 4.5)
    for role in ('border', 'border_focus'):
        p[role] = readable(p[role], p['background'], 3)
    # White text on the workspace pill and selection must stay readable too.
    for role in ('workspace', 'selection'):
        while contrast(p['foreground'], p[role]) < 4.5:
            p[role] = hexcolor(v * .92 for v in rgb(p[role]))
    validate_palette(p, base)
    return p


def validate_palette(palette, base):
    if set(palette) != set(base):
        raise ValueError('Semantic palette roles do not match Frosted Glass')
    for color in palette.values():
        rgb(color)
    if luminance(palette['background']) > .06:
        raise ValueError('Hyprixe requires a dark background')
    for surface in ('background', 'surface', 'surface_alt'):
        for role in ('foreground', 'foreground_muted'):
            if contrast(palette[role], palette[surface]) < 4.5:
                raise ValueError(f'Insufficient contrast: {role}/{surface}')
    if contrast(palette['foreground'], palette['selection']) < 4.5:
        raise ValueError('Insufficient selection contrast')
    for role in ('accent', 'accent_alt', 'border', 'border_focus'):
        if contrast(palette[role], palette['background']) < 3:
            raise ValueError('Invisible accent/border: ' + role)


def render(resources, palette):
    validate_palette(palette, defaults(resources))
    values = dict(palette)
    for role, color in palette.items():
        values[role + '_hex'] = color[1:]
        values[role + '_rgb'] = ', '.join(str(round(v * 255)) for v in rgb(color))
    result = {}
    for name in FILES:
        template = (resources / 'templates' / name).read_text()
        try:
            content = TOKEN.sub(lambda match: values[match[1]], template)
        except KeyError as exc:
            raise ValueError('Unknown semantic template role: ' + str(exc)) from exc
        if TOKEN.search(content) or '{{' in content or '}}' in content:
            raise ValueError('Unresolved template token: ' + name)
        result[name] = content
    return result


def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, timeout=45, **kwargs)


def validate_outputs(directory, native=True):
    """Constrained colour-only grammar plus available native parsers.

    Hyprland/Hyprlock have no independent fragment parser: whitelist their
    generated grammar; luac validates the Lua syntax without a compositor.
    """
    for name in FILES:
        text = (directory / name).read_text()
        if not text.strip() or TOKEN.search(text) or '{{' in text:
            raise ValueError('Empty/unresolved output: ' + name)
        if name.endswith('.css'):
            if not all(re.fullmatch(r'@define-color hx_[a-z_]+ #[0-9a-f]{6};', line)
                       for line in text.splitlines()):
                raise ValueError('Invalid CSS colour declarations: ' + name)
        elif name == 'kitty.conf':
            allowed = r'(?:background|foreground|cursor|cursor_text_color|selection_background|selection_foreground|url_color|color(?:[0-9]|1[0-5]))'
            if not all(re.fullmatch(allowed + r'\s+#[0-9a-f]{6}', line) for line in text.splitlines()):
                raise ValueError('Invalid Kitty colours')
        elif name == 'rofi.rasi':
            if not re.fullmatch(r'\* \{\n(?:    [a-z-]+: (?:#[0-9a-f]{6}|rgba\(\d+, \d+, \d+, 0\.\d+\));\n)+\}\n', text):
                raise ValueError('Invalid Rasi colours')
        elif name == 'hyprlock.conf':
            if not all(re.fullmatch(r'\$hx_[a-z]+ = rgba\([0-9a-f]{8}\)(?: rgba\([0-9a-f]{8}\) 45deg)?', line)
                       for line in text.splitlines()):
                raise ValueError('Invalid Hyprlock variables')
        elif name == 'hyprland.lua':
            stripped = re.sub(r'--[^\n]*', '', text)
            stripped = re.sub(r'"rgba\([0-9a-f]{8}\)"', 'COLOR', stripped)
            identifiers = set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*', stripped))
            allowed = {'hl', 'config', 'general', 'col', 'active_border', 'inactive_border',
                       'colors', 'angle', 'group', 'border_active', 'border_inactive',
                       'decoration', 'shadow', 'color', 'COLOR'}
            if not identifiers <= allowed or any(c in stripped for c in "'[];:"):
                raise ValueError('Hyprland output is not a colour-only fragment')
        if not native:
            continue
        commands = []
        if name == 'hyprland.lua' and shutil.which('luac'):
            commands.append(['luac', '-p', str(directory / name)])
        if name == 'kitty.conf' and shutil.which('kitty'):
            commands.append(['kitty', '+runpy', KITTY_PARSER, str(directory / name)])
        if name == 'rofi.rasi' and shutil.which('rofi'):
            commands.append(['rofi', '-no-config', '-theme', str(directory / name), '-dump-theme'])
        if name.endswith('.css'):
            # GTK is optional for source-only checks, required by Debian deps.
            probe = run([sys.executable, '-c', "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk"])
            if probe.returncode == 0:
                commands.append([sys.executable, '-c', GTK_PARSER, str(directory / name)])
        for command in commands:
            parser_env = dict(os.environ, GDK_BACKEND='x11', DISPLAY='', WAYLAND_DISPLAY='') if name.endswith('.css') else None
            result = run(command, env=parser_env)
            if result.returncode or result.stderr.strip():
                raise ValueError(f'Native parser rejected {name}: {(result.stderr or result.stdout).strip()}')


def atomic(path, data):
    temporary = path.with_name('.tmp-' + uuid.uuid4().hex)
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def image_valid(path):
    from PIL import Image
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file() or any(c in str(path) for c in '\n\r\0'):
        raise ValueError('Wallpaper must be a regular image file')
    try:
        with Image.open(path) as image:
            if image.width * image.height > 100_000_000:
                raise ValueError('Wallpaper exceeds 100 megapixels')
            image.verify()
        # JPEG verify() does little work: decode before replacing a background.
        with Image.open(path) as image:
            image.load()
    except (OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValueError('Cannot decode wallpaper: ' + str(exc)) from exc
    return path


class Engine:
    def __init__(self, resources=None):
        home = Path.home()
        self.resources = resources or Path(__file__).resolve().parent
        self.cache = Path(os.environ.get('XDG_CACHE_HOME', home / '.cache')) / 'hyprixe/theme'
        self.state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'hyprixe'
        self.data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')) / 'hyprixe'
        self.current = self.cache / 'current'
        self.base = defaults(self.resources)
        # Refuse source-tree runtime state, including XDG overrides into a checkout.
        for path in (self.cache, self.state):
            if not path.is_absolute() or '..' in path.parts:
                raise ValueError('XDG paths must be absolute and canonical')
            if any((p / '.git').exists() for p in (path.resolve(), *path.resolve().parents)):
                raise ValueError('Runtime state must stay outside the Git checkout')
            for parent in (path, *path.parents):
                if parent.is_symlink():
                    raise ValueError('Runtime state cannot follow directory symlinks')

    @contextmanager
    def locked(self):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        # Keep the lock outside disposable generations. Never unlink it while held.
        lock_path = self.cache.parent / 'theme.lock'
        if lock_path.is_symlink():
            raise ValueError('Unsafe theme lock')
        with lock_path.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.cache.exists() and not (self.cache / '.owner').is_file():
                raise ValueError('Refusing an unowned theme cache: ' + str(self.cache))
            self.cache.mkdir(mode=0o700, exist_ok=True)
            atomic(self.cache / '.owner', OWNER)
            (self.cache / 'generations').mkdir(exist_ok=True)
            self.state.mkdir(parents=True, exist_ok=True)
            yield

    def version(self):
        if not shutil.which('wallust'):
            return None
        result = run(['wallust', '--version'])
        match = re.match(r'wallust (\d+\.\d+\.\d+)(?=\s|$)', result.stdout)
        return match[1] if result.returncode == 0 and match else None

    def fingerprint(self):
        h = hashlib.sha256()
        for relative in ('engine.py', 'wallust.toml', 'raw.json', 'defaults/frosted-glass.json',
                         *('templates/' + name for name in FILES)):
            h.update((self.resources / relative).read_bytes())
        return h.hexdigest()

    def read(self, path=None):
        path = path or self.current
        try:
            resolved = path.resolve(strict=True)
            if resolved.parent != self.cache / 'generations' or resolved.is_symlink():
                return None
            meta = json.loads((resolved / 'metadata.json').read_text())
            required = {'format', 'enabled', 'wallpaper', 'wallpaper_hash', 'key',
                        'source', 'created', 'wallust_version', 'files'}
            if not required <= meta.keys() or meta['format'] != 1 or type(meta['enabled']) is not bool:
                return None
            if not Path(meta['wallpaper']).is_absolute() or any(c in meta['wallpaper'] for c in '\r\n\0'):
                return None
            if not all(re.fullmatch('[0-9a-f]{64}', meta[key]) for key in ('key', 'wallpaper_hash')):
                return None
            if meta['source'] not in ('wallust', 'wallust-calibrated', 'frosted-glass', 'fallback'):
                return None
            datetime.fromisoformat(meta['created'])
            if (resolved / 'wallpaper-path').read_text().strip() != meta['wallpaper']:
                return None
            palette = json.loads((resolved / 'palette.json').read_text())
            validate_palette(palette, self.base)
            if set(meta['files']) != set(FILES) | {'palette.json'}:
                return None
            if any((resolved / name).is_symlink() or sha(resolved / name) != digest for name, digest in meta['files'].items()):
                return None
            validate_outputs(resolved, native=False)
            return meta
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def wallpaper(self):
        meta = self.read()
        if meta and meta.get('wallpaper'):
            return Path(meta['wallpaper'])
        # Recover the last path even when a generated colour file is corrupt.
        try:
            saved = (self.state / 'wallpaper').read_text().strip()
            if saved:
                return Path(saved)
        except OSError:
            pass
        return self.data / 'wallpapers/min_forest.jpg'

    def extract(self, wallpaper, directory):
        if self.version() != WALLUST_VERSION:
            raise ValueError(f'Wallust {WALLUST_VERSION} required (found {self.version() or "absent"})')
        target = directory / 'raw.json'
        config = (self.resources / 'wallust.toml').read_text().replace('"@RAW_TARGET@"', json.dumps(str(target)))
        (directory / 'wallust.toml').write_text(config)
        result = run(['wallust', '--config-file', str(directory / 'wallust.toml'),
                      '--templates-dir', str(self.resources), '--skip-sequences', '--no-hooks',
                      '--quiet', 'run', str(wallpaper), '--no-cache', '--dynamic-threshold'])
        if result.returncode or not target.is_file():
            raise ValueError('Wallust extraction failed: ' + (result.stderr.strip() or str(result.returncode)))
        return json.loads(target.read_text())

    def publish(self, generation):
        temporary = self.cache / ('.current-' + uuid.uuid4().hex)
        try:
            temporary.symlink_to(generation.relative_to(self.cache), target_is_directory=True)
            os.replace(temporary, self.current)
        finally:
            temporary.unlink(missing_ok=True)

    def mirrors(self):
        # These stable links point through the same atomic generation pointer.
        for name, target in (('wallpaper', self.current / 'wallpaper-path'),
                             ('theme.json', self.current / 'metadata.json')):
            path = self.state / name
            if path.is_symlink() and os.readlink(path) == str(target):
                continue
            if path.exists() or path.is_symlink():
                raise ValueError('Refusing to replace unowned state: ' + str(path))
            path.symlink_to(target)

    def apply_image(self, wallpaper):
        result = run(['awww', 'img', '--resize', 'crop', '--transition-type', 'none', str(wallpaper)])
        if result.returncode:
            raise ValueError('awww could not apply wallpaper: ' + result.stderr.strip())

    def reload(self):
        warnings = []
        if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') and shutil.which('hyprctl'):
            result = run(['hyprctl', 'reload'])
            if result.returncode:
                raise ValueError('Hyprland reload failed: ' + result.stderr.strip())
            errors = run(['hyprctl', 'configerrors', '-j'])
            if errors.returncode == 0 and errors.stdout.strip() not in ('', '[]', '{}', 'null'):
                raise ValueError('Hyprland configerrors: ' + errors.stdout.strip())
        # SIGUSR1 in Kitty 0.41 (Trixie) reloads config, SIGUSR2 is Waybar's
        # supported reload. Signal only our user's processes with a handler.
        for name, signum in (('waybar', signal.SIGUSR2), ('kitty', signal.SIGUSR1)):
            if not shutil.which('pgrep'):
                continue
            result = run(['pgrep', '-u', str(os.getuid()), '-x', name])
            for value in result.stdout.split():
                try:
                    pid = int(value)
                    status = Path(f'/proc/{pid}/status').read_text()
                    caught = int(re.search(r'^SigCgt:\s*([0-9a-f]+)', status, re.M)[1], 16)
                    if caught & (1 << (signum - 1)):
                        os.kill(pid, signum)
                except (OSError, ValueError, TypeError):
                    warnings.append(name + ': reload unavailable')
        if shutil.which('swaync-client') and shutil.which('pgrep'):
            if run(['pgrep', '-u', str(os.getuid()), '-x', 'swaync']).returncode == 0:
                result = run(['swaync-client', '--reload-css'])
                if result.returncode:
                    warnings.append('SwayNC: CSS reload failed')
        return warnings

    def transact(self, wallpaper=None, *, enabled=None, force=False, apply=True, reload=True, use_default=False, restore=False):
        with self.locked():
            old = self.read()
            previous = self.current.resolve() if old else None
            is_enabled = enabled if enabled is not None else old.get('enabled', True) if old else True
            path = wallpaper or self.wallpaper()
            try:
                path = image_valid(path)
            except (OSError, ValueError) as exc:
                if wallpaper is not None:
                    raise ValueError('Invalid wallpaper; previous theme preserved: ' + str(exc)) from exc
                path = image_valid(self.data / 'wallpapers/min_forest.jpg')
                print('WARNING: Saved wallpaper unavailable; using Frosted Glass wallpaper.', file=sys.stderr)
            digest = sha(path)
            fingerprint = self.fingerprint()
            key = hashlib.sha256(f'{digest}:{fingerprint}:{is_enabled}:{use_default}'.encode()).hexdigest()
            if old and old['key'] == key and old['wallpaper'] == str(path) and not force:
                if apply and restore:
                    self.apply_image(path)
                return old
            # Validate state link ownership before changing wallpaper or current.
            self.mirrors()
            with tempfile.TemporaryDirectory(prefix='.build-', dir=self.cache / 'generations') as temporary:
                stage = Path(temporary)
                palette, source = dict(self.base), 'frosted-glass'
                if is_enabled and not use_default:
                    try:
                        cached = None if force else next((p for p in (self.cache / 'generations').iterdir()
                                  if not p.name.startswith('.') and (self.read(p) or {}).get('key') == key
                                  and self.read(p).get('source') in ('wallust', 'wallust-calibrated')), None)
                        raw = None if cached else self.extract(path, stage)
                        # Hash calibration preserves the exact v1.1 paint for the
                        # bundled image, even when it has been renamed/copied.
                        reference = self.data / 'wallpapers/min_forest.jpg'
                        calibrated = reference.is_file() and digest == sha(reference)
                        palette = json.loads((cached / 'palette.json').read_text()) if cached else normalize(raw, self.base)
                        if calibrated:
                            palette = dict(self.base)
                        source = 'wallust-calibrated' if calibrated else 'wallust'
                    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
                        source = 'fallback'
                        print('WARNING: ' + str(exc) + '; using Frosted Glass colours.', file=sys.stderr)
                try:
                    outputs = render(self.resources, palette)
                    for name, content in outputs.items():
                        (stage / name).write_text(content)
                    validate_outputs(stage)
                except (OSError, ValueError, subprocess.SubprocessError):
                    if old:
                        raise  # Never publish an invalid template over a good generation.
                    # A validated installation-time default remains usable even
                    # if editable templates are later damaged.
                    for name in FILES:
                        shutil.copyfile(self.resources / 'fallback' / name, stage / name)
                    palette, source = dict(self.base), 'fallback'
                    validate_outputs(stage)
                if sha(path) != digest:
                    raise ValueError('Wallpaper changed during generation; retry')
                atomic(stage / 'palette.json', json.dumps(palette, indent=2) + '\n')
                atomic(stage / 'wallpaper-path', str(path) + '\n')
                meta = {'format': 1, 'enabled': is_enabled, 'wallpaper': str(path),
                        'wallpaper_hash': digest, 'key': key, 'source': source,
                        'created': datetime.now(timezone.utc).isoformat(),
                        'wallust_version': self.version(), 'files': {name: sha(stage / name) for name in (*FILES, 'palette.json')}}
                atomic(stage / 'metadata.json', json.dumps(meta, indent=2) + '\n')
                destination = self.cache / 'generations' / uuid.uuid4().hex
                os.replace(stage, destination)
                changed_image = False
                try:
                    # Preparation precedes presentation: one wallpaper update,
                    # with all colour files already validated and complete.
                    if apply and (restore or not old or old['wallpaper'] != str(path) or old['wallpaper_hash'] != digest):
                        self.apply_image(path)
                        changed_image = True
                    self.publish(destination)
                    if reload:
                        for warning in self.reload():
                            print('WARNING: ' + warning, file=sys.stderr)
                except BaseException:
                    if previous:
                        self.publish(previous)
                        if changed_image:
                            self.apply_image(Path(old['wallpaper']))
                        if reload:
                            self.reload()
                    elif changed_image:
                        # Recovery without an intact predecessor must still
                        # leave importable defaults, never an empty current/.
                        emergency = self.cache / 'generations' / uuid.uuid4().hex
                        shutil.copytree(self.resources / 'fallback', emergency)
                        validate_outputs(emergency)
                        atomic(emergency / 'palette.json', json.dumps(self.base, indent=2) + '\n')
                        atomic(emergency / 'wallpaper-path', str(path) + '\n')
                        fallback_meta = dict(meta, source='fallback', key=hashlib.sha256((key + ':recovery').encode()).hexdigest())
                        fallback_meta['files'] = {name: sha(emergency / name) for name in (*FILES, 'palette.json')}
                        atomic(emergency / 'metadata.json', json.dumps(fallback_meta, indent=2) + '\n')
                        self.publish(emergency)
                    raise
                return meta


def main(argv=None):
    parser = argparse.ArgumentParser(description='Hyprixe dynamic Frosted Glass colours')
    parser.add_argument('action', choices=('apply', 'refresh', 'status', 'default', 'enable', 'disable', 'restore', 'init'))
    parser.add_argument('wallpaper', nargs='?')
    args = parser.parse_args(argv)
    if (args.action == 'apply') != (args.wallpaper is not None):
        parser.error('apply requires exactly one image; other actions take no image')
    try:
        engine = Engine()
        if args.action == 'status':
            meta = engine.read()
            if not meta:
                raise ValueError('No valid generated theme; run hyprixe-theme refresh')
            print('dynamic theming: ' + ('enabled' if meta['enabled'] else 'disabled'))
            for key in ('wallpaper', 'wallpaper_hash', 'source', 'created'):
                print(key.replace('_', ' ') + ': ' + str(meta[key]))
            print('Wallust version: ' + str(engine.version() or 'absent'))
            return 0
        action = args.action
        wallpaper = Path(args.wallpaper) if args.wallpaper else None
        if action == 'init' and not engine.current.exists() and shutil.which('awww'):
            # v1.1 migration: use the actual active image when the daemon knows
            # it; a session without a daemon keeps the bundled min_forest.
            query = run(['awww', 'query'])
            images = re.findall(r'currently displaying: image: (.+)', query.stdout)
            if query.returncode == 0 and images and len(set(images)) == 1:
                try:
                    wallpaper = image_valid(images[0])
                except (OSError, ValueError):
                    pass
        engine.transact(wallpaper,
                        enabled=False if action == 'disable' else True if action == 'enable' else None,
                        force=action in ('refresh', 'default', 'enable', 'disable'),
                        use_default=action == 'default', apply=action != 'init',
                        reload=action != 'init', restore=action == 'restore')
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
