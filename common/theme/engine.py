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
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from hyprland_errors import parse_config_errors

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


def oklab(color):
    """D65 sRGB -> Oklab, using Ottosson's published 2021 matrices."""
    r, g, b = (v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb(color))
    l = (.4122214708*r + .5363325363*g + .0514459929*b) ** (1/3)
    m = (.2119034982*r + .6806995451*g + .1073969566*b) ** (1/3)
    s = (.0883024619*r + .2817188376*g + .6299787005*b) ** (1/3)
    return (.2104542553*l + .7936177850*m - .0040720468*s,
            1.9779984951*l - 2.4285922050*m + .4505937099*s,
            .0259040371*l + .7827717662*m - .8086757660*s)


def lch(color):
    lightness, a, b = oklab(color)
    return lightness, math.hypot(a, b), (math.atan2(b, a) / math.tau) % 1


def distance(a, b):
    """Euclidean Oklab distance, on the 0..1 lightness scale (not x100)."""
    return math.dist(oklab(a), oklab(b))


def tinted(lightness, chroma, hue):
    """Oklch -> sRGB; reduce chroma at fixed L/h to stay inside the gamut."""
    def channels(c):
        a, b = c * math.cos(hue * math.tau), c * math.sin(hue * math.tau)
        l = (lightness + .3963377774*a + .2158037573*b) ** 3
        m = (lightness - .1055613458*a - .0638541728*b) ** 3
        s = (lightness - .0894841775*a - 1.2914855480*b) ** 3
        return (4.0767416621*l - 3.3077115913*m + .2309699292*s,
                -1.2684380046*l + 2.6097574011*m - .3413193965*s,
                -.0041960863*l - .7034186147*m + 1.7076147010*s)
    low, high = 0., chroma
    values = channels(chroma)
    if not all(-1e-7 <= v <= 1 + 1e-7 for v in values):
        for _ in range(14):
            candidate = (low + high) / 2
            if all(0 <= v <= 1 for v in channels(candidate)):
                low = candidate
            else:
                high = candidate
        values = channels(low)
    return hexcolor(12.92*v if v <= .0031308 else 1.055*v**(1/2.4) - .055 for v in values)


def blend(color, background, opacity):
    """Encoded-sRGB alpha composition, for existing GTK/QML paint checks."""
    return hexcolor(a * opacity + b * (1-opacity) for a, b in zip(rgb(color), rgb(background)))


def hue_distance(a, b):
    return min(abs(a-b), 1-abs(a-b))


def accent_candidates(colors):
    result = []
    for color in sorted(set(c.lower() for c in colors)):
        lightness, chroma, hue = lch(color)
        if chroma < .025:
            continue
        visibility = max(.05, min(1., (lightness-.15)/.25, (.99-lightness)/.20))
        score = min(chroma, .18) * visibility
        # A dull brown may be genuine, but should not displace a useful colour.
        if .10 < hue < .23 and lightness < .62 and chroma < .11:
            score *= .65
        result.append((score, color, lightness, chroma, hue))
    return sorted(result, reverse=True)


def lit_accent(lightness, chroma, hue, backgrounds):
    for step in range(8):
        if lightness + step * .01 > .85 + 1e-9:
            break
        color = tinted(lightness + step * .01, chroma, hue)
        if all(contrast(color, b) >= 4.5 for b in backgrounds):
            return color
    raise ValueError('Cannot fit a readable accent inside the Frosted Glass range')


def normalize(raw, base):
    colors = raw['colors']
    if len(colors) != 16:
        raise ValueError('Wallust must return exactly 16 RGB colours')
    for color in [raw['background'], raw['foreground'], *colors]:
        rgb(color)
    candidates = accent_candidates(colors)
    if candidates:
        _, _, source_lightness, source_chroma, hue = candidates[0]
    else:
        source_lightness, source_chroma, hue = max((lch(c) for c in colors), key=lambda c: (c[1], c[0], c[2]))
        if source_chroma < .012:
            hue = lch(base['accent'])[2]
    p = dict(base)
    tone = max(-.01, min(.01, (source_lightness-.60) * .04))
    tint = max(.012, min(.022, source_chroma * .14))
    for role, lightness, chroma in (
        ('background', .225+tone, tint*.80), ('surface', .310+tone, tint),
        ('surface_alt', .375+tone, tint), ('foreground', .94, .007),
        ('foreground_muted', .80, .014), ('border', .54, .025),
        ('border_focus', .63, .065), ('border_secondary', .35, .030),
        ('selection', .42, .065), ('workspace', .43, .075),
    ):
        p[role] = tinted(lightness, chroma, hue)
    # Keep accent text readable over the unchanged translucent Waybar layers,
    # including a white wallpaper. No opacity/geometry compensation is needed.
    bar = blend(p['background'], '#ffffff', .76)
    backgrounds = (p['surface_alt'], blend(p['surface'], bar, .32), blend(p['border_secondary'], bar, .45))
    p['accent'] = lit_accent(.79, max(.09, min(.13, source_chroma*.65)), hue, backgrounds)
    alternatives = []
    for score, color, lightness, chroma, other_hue in candidates:
        if hue_distance(hue, other_hue) < .10:
            continue
        alternate = lit_accent(.80, max(.09, min(.12, chroma*.65)), other_hue, backgrounds)
        if distance(p['accent'], alternate) >= .075:
            alternatives.append((score * (1 - .4*hue_distance(hue, other_hue)), color, alternate))
    if alternatives:
        p['accent_alt'] = max(alternatives)[2]
    else:
        # Monochrome: an analogous hue at most 54 degrees away, not a foreign
        # complementary workspace colour. Quantized distance is checked below.
        offset = -.15 if hue >= .58 or .15 < hue < .30 else .15
        p['accent_alt'] = lit_accent(.80, .12, (hue+offset) % 1, backgrounds)
    for role, lightness, chroma in (('success', .82, .13), ('warning', .83, .13), ('error', .81, .15)):
        p[role] = tinted(lightness, chroma, lch(base[role])[2])
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
    for role in ('selection', 'workspace', 'border_secondary'):
        if contrast(palette['foreground'], palette[role]) < 4.5:
            raise ValueError('Insufficient text contrast: ' + role)
    for role in ('accent', 'accent_alt'):
        if contrast(palette['background'], palette[role]) < 4.5:
            raise ValueError('Insufficient dark text on accent: ' + role)
    for role in ('accent', 'accent_alt', 'border', 'border_focus'):
        if contrast(palette[role], palette['background']) < 3:
            raise ValueError('Invisible accent/border: ' + role)
    # Preserve the complete historical/default palette and existing fallback.
    # Additional tonal envelopes apply only to transformed wallpaper palettes.
    if palette == base:
        return
    for role in ('background', 'surface', 'surface_alt'):
        if not .003 <= luminance(palette[role]) <= .065 or lch(palette[role])[1] > .025:
            raise ValueError('Surface outside dark neutral range: ' + role)
    if not luminance(palette['background']) < luminance(palette['surface']) < luminance(palette['surface_alt']):
        raise ValueError('Surface hierarchy is not ordered')
    for a, b, minimum in (('background', 'surface', .075), ('surface', 'surface_alt', .055),
                          ('accent', 'accent_alt', .075), ('foreground', 'foreground_muted', .12)):
        if distance(palette[a], palette[b]) < minimum:
            raise ValueError('Semantic colours too close: ' + a + '/' + b)
    for role in ('accent', 'accent_alt'):
        lightness, chroma, _ = lch(palette[role])
        if not .77 <= lightness <= .855 or not .035 <= chroma <= .135:
            raise ValueError('Accent outside restrained chroma/lightness range: ' + role)
        if contrast(palette[role], palette['surface_alt']) < 4.5:
            raise ValueError('Insufficient accent text contrast: ' + role)
    for role in ('success', 'warning', 'error'):
        if contrast(palette[role], palette['surface_alt']) < 4.5:
            raise ValueError('Insufficient status contrast: ' + role)


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
            os.fchmod(stream.fileno(), 0o600)
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
        self.current_wallpaper = self.data / 'current-wallpaper'
        self.current = self.cache / 'current'
        self.state_file = self.state / 'theme.json'
        self.base = defaults(self.resources)
        # Refuse source-tree runtime state, including XDG overrides into a checkout.
        for path in (self.cache, self.state, self.data):
            if not path.is_absolute() or '..' in path.parts:
                raise ValueError('XDG paths must be absolute and canonical')
            if any((p / '.git').exists() for p in (path.resolve(), *path.resolve().parents)):
                raise ValueError('Runtime state must stay outside the Git checkout')
            for parent in (path, *path.parents):
                if parent.is_symlink():
                    raise ValueError('Runtime state cannot follow directory symlinks')

    @contextmanager
    def locked(self):
        self.state.mkdir(parents=True, exist_ok=True)
        # This lock must survive deletion of the entire cache/hyprixe tree.
        lock_path = self.state / 'theme.lock'
        if lock_path.is_symlink():
            raise ValueError('Unsafe theme lock')
        with lock_path.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def ensure_cache(self):
        if self.cache.exists() and not (self.cache / '.owner').is_file():
            raise ValueError('Refusing an unowned theme cache: ' + str(self.cache))
        self.cache.mkdir(parents=True, mode=0o700, exist_ok=True)
        if not (self.cache / '.owner').exists():
            atomic(self.cache / '.owner', OWNER)
        (self.cache / 'generations').mkdir(exist_ok=True)

    @staticmethod
    def validate_state(saved):
        if not isinstance(saved, dict) or set(saved) != {'format', 'enabled', 'wallpaper', 'wallpaper_hash'}:
            raise ValueError('Invalid state fields')
        if saved['format'] != 2 or type(saved['enabled']) is not bool:
            raise ValueError('Invalid state format/preference')
        wallpaper, digest = saved['wallpaper'], saved['wallpaper_hash']
        if wallpaper is not None and (not isinstance(wallpaper, str) or not wallpaper or
                not Path(wallpaper).is_absolute() or '..' in Path(wallpaper).parts or
                any(c in wallpaper for c in '\r\n\0')):
            raise ValueError('Invalid persistent wallpaper path')
        if digest is not None and (not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
            raise ValueError('Invalid persistent wallpaper hash')
        if wallpaper is None and digest is not None:
            raise ValueError('Wallpaper hash has no associated path')
        return saved

    def save_state(self, saved):
        """Called under the persistent lock; never follow an arbitrary symlink."""
        self.validate_state(saved)
        if self.state_file.is_symlink() and os.readlink(self.state_file) != str(self.current / 'metadata.json'):
            raise ValueError('Refusing to replace unowned state: ' + str(self.state_file))
        text = json.dumps(saved, indent=2) + '\n'
        if not self.state_file.is_symlink() and self.state_file.is_file() and self.state_file.read_text() == text:
            return
        atomic(self.state_file, text)
        descriptor = os.open(self.state, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def load_state(self, *, migrate=False):
        """Read durable preferences, or conservatively import the pre-release links.

        A corrupt v2 file is never replaced using cache guesses. A legacy mode
        is enabled only when the current legacy metadata is unambiguous.
        """
        legacy_link = self.state_file.is_symlink()
        if legacy_link and os.readlink(self.state_file) != str(self.current / 'metadata.json'):
            raise ValueError('Refusing to replace unowned state: ' + str(self.state_file))
        if not legacy_link and self.state_file.exists():
            try:
                return self.validate_state(json.loads(self.state_file.read_text()))
            except (OSError, ValueError, TypeError) as exc:
                raise ValueError('Persistent theme state is invalid; preserve/repair ' + str(self.state_file)) from exc
        legacy_wallpaper = self.state / 'wallpaper'
        managed_wallpaper = legacy_wallpaper.is_symlink() and os.readlink(legacy_wallpaper) == str(self.current / 'wallpaper-path')
        if (legacy_wallpaper.exists() or legacy_wallpaper.is_symlink()) and not managed_wallpaper:
            raise ValueError('Refusing to replace unowned state: ' + str(legacy_wallpaper))
        legacy = legacy_link or managed_wallpaper or self.current.exists() or self.current.is_symlink() or (self.cache / 'generations').exists()
        if not legacy:
            return None
        meta = {}
        try:
            generation = self.current.resolve(strict=True)
            if generation.parent == self.cache / 'generations':
                candidate = json.loads((generation / 'metadata.json').read_text())
                if isinstance(candidate, dict):
                    meta = candidate
        except (OSError, ValueError):
            pass
        saved = {'format': 2, 'enabled': False, 'wallpaper': None, 'wallpaper_hash': None}
        try:
            candidate = dict(saved, enabled=meta['enabled'] if meta.get('format') == 1 and 'state_hash' not in meta else False,
                             wallpaper=meta['wallpaper'], wallpaper_hash=meta['wallpaper_hash'])
            self.validate_state(candidate)
            if candidate['wallpaper'] is not None and candidate['wallpaper_hash'] is not None:
                saved = candidate
        except (KeyError, ValueError, TypeError):
            pass
        if saved['wallpaper'] is None and managed_wallpaper:
            try:
                path = legacy_wallpaper.read_text().strip()
                candidate = dict(saved, wallpaper=path)
                self.validate_state(candidate)
                saved = candidate
                if Path(path).is_file():
                    saved['wallpaper_hash'] = sha(path)
            except (OSError, ValueError):
                pass
        if migrate:
            self.save_state(saved)
            # Only remove the exact legacy link owned by this engine.
            if managed_wallpaper:
                legacy_wallpaper.unlink()
        return saved

    @staticmethod
    def state_hash(saved):
        return hashlib.sha256(json.dumps(saved, sort_keys=True).encode()).hexdigest()

    def cache_status(self, saved):
        if not self.current.exists() and not self.current.is_symlink():
            return 'missing'
        meta = self.read()
        return 'valid' if meta and saved and meta.get('state_hash') == self.state_hash(saved) else 'invalid'

    def cache_reason(self, saved):
        """Explain rejection without weakening any palette/manifest checks."""
        meta = self.read()
        if meta and saved and meta.get('state_hash') != self.state_hash(saved):
            return ('generation state fingerprint differs from persistent state; generation wallpaper: '
                    + meta['wallpaper'] + '; generation enabled: ' + str(meta['enabled'])
                    + '; persistent enabled: ' + str(saved['enabled']) + '; run hyprixe-theme refresh')
        return 'generation files, metadata or checksums are invalid; run hyprixe-theme refresh'

    def version(self):
        if not shutil.which('wallust'):
            return None
        result = run(['wallust', '--version'])
        match = re.match(r'wallust (\d+\.\d+\.\d+)(?=\s|$)', result.stdout)
        return match[1] if result.returncode == 0 and match else None

    def fingerprint(self):
        h = hashlib.sha256()
        for relative in ('engine.py', 'hyprland_errors.py', 'wallust.toml', 'raw.json', 'defaults/frosted-glass.json',
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
            if not isinstance(meta, dict) or not required <= meta.keys() or meta['format'] != 1 or type(meta['enabled']) is not bool:
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

    def wallpaper(self, saved=None):
        saved = self.load_state() if saved is None else saved
        if saved and saved['wallpaper']:
            return Path(saved['wallpaper'])
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

    def apply_image(self, wallpaper):
        result = run(['awww', 'img', '--resize', 'crop', '--transition-type', 'none', str(wallpaper)])
        if result.returncode:
            raise ValueError('awww could not apply wallpaper: ' + result.stderr.strip())

    def guard_wallpaper_link(self):
        link = self.current_wallpaper
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or link.lstat().st_uid != os.getuid():
                raise ValueError('Refusing an unmanaged current-wallpaper: ' + str(link))

    def link_wallpaper(self, wallpaper):
        """Derived presentation path, never a second source of selection state."""
        target = image_valid(wallpaper)
        self.data.mkdir(parents=True, exist_ok=True)
        self.guard_wallpaper_link()
        link = self.current_wallpaper
        temporary = self.data / ('.wallpaper-' + uuid.uuid4().hex)
        try:
            temporary.symlink_to(target)
            os.replace(temporary, link)
            directory_fd = os.open(self.data, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)

    def sync_login_theme(self, wallpaper):
        # Profiles may provide this optional integration. The portable engine
        # knows neither system destinations nor privileged mechanisms.
        helper = shutil.which('hyprixe-login-theme-sync')
        if not helper:
            installed = Path.home() / '.local/bin/hyprixe-login-theme-sync'
            if installed.is_file() and os.access(installed, os.X_OK):
                helper = str(installed)
        if helper:
            try:
                result = run([helper, str(wallpaper), str(self.current / 'palette.json')])
                if result.returncode:
                    raise ValueError((result.stderr or result.stdout).strip())
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                print('WARNING: Login theme sync failed; session theme is active: ' + str(exc), file=sys.stderr)

    def reload(self):
        warnings = []
        if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') and shutil.which('hyprctl'):
            result = run(['hyprctl', 'reload'])
            if result.returncode:
                raise ValueError('Hyprland reload failed: ' + result.stderr.strip())
            errors = run(['hyprctl', 'configerrors', '-j'])
            if errors.returncode:
                raise ValueError('Hyprland configerrors query failed: ' + (errors.stderr or errors.stdout).strip())
            messages = parse_config_errors(errors.stdout)
            if messages:
                raise ValueError('Hyprland configerrors: ' + '\n'.join(messages))
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

    def transact(self, wallpaper=None, *, enabled=None, force=False, apply=True, reload=True, use_default=False, restore=False, initialize=False, reapply=False):
        with self.locked():
            state_error = False
            try:
                saved = self.load_state(migrate=True)
            except ValueError:
                if not restore:
                    raise
                saved, state_error = None, True
                print('WARNING: Invalid theme state; restoring defaults without changing preferences.', file=sys.stderr)
            def persist(value):
                if not state_error:
                    self.save_state(value)
            fresh = saved is None
            if fresh:
                # Public commands preserve a safe disabled preference when no
                # history exists. Only first installation init opts in by default.
                saved = {'format': 2, 'enabled': bool(initialize), 'wallpaper': None, 'wallpaper_hash': None}
            if enabled is not None:
                saved = dict(saved, enabled=enabled)
            # Record an explicit choice even if extraction/rendering later fails.
            persist(saved)
            old = self.read()
            previous = self.current.resolve() if old else None
            is_enabled = saved['enabled']
            if initialize and fresh and wallpaper is None and shutil.which('awww'):
                query = run(['awww', 'query'])
                images = re.findall(r'currently displaying: image: (.+)', query.stdout)
                if query.returncode == 0 and images and len(set(images)) == 1:
                    try:
                        wallpaper = image_valid(images[0])
                    except (OSError, ValueError):
                        pass
            path = self.data / 'wallpapers/min_forest.jpg' if use_default else wallpaper or self.wallpaper(saved)
            fallback_wallpaper = False
            try:
                path = image_valid(path)
            except (OSError, ValueError) as exc:
                if wallpaper is not None:
                    raise ValueError('Invalid wallpaper; previous theme preserved: ' + str(exc)) from exc
                path = image_valid(self.data / 'wallpapers/min_forest.jpg')
                fallback_wallpaper = True
                print('WARNING: Selected wallpaper unavailable; using Frosted Glass wallpaper and preserving its saved path/preference.', file=sys.stderr)
            digest = sha(path)
            self.guard_wallpaper_link()
            selected = saved if fallback_wallpaper and saved['wallpaper'] else dict(saved, wallpaper=str(path), wallpaper_hash=digest)
            self.ensure_cache()
            fingerprint = self.fingerprint()
            # default now selects the calibrated bundled image. Its generated
            # palette is also correct for restore, without a second extraction.
            key = hashlib.sha256(f'{digest}:{fingerprint}:{is_enabled}'.encode()).hexdigest()
            if old and old['key'] == key and old['wallpaper'] == str(path) and old.get('state_hash') == self.state_hash(selected) and not force:
                self.link_wallpaper(path)
                if apply and (restore or reapply):
                    self.apply_image(path)
                persist(selected)
                self.sync_login_theme(path)
                return old
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
                        'state_hash': self.state_hash(selected),
                        'created': datetime.now(timezone.utc).isoformat(),
                        'wallust_version': self.version(), 'files': {name: sha(stage / name) for name in (*FILES, 'palette.json')}}
                atomic(stage / 'metadata.json', json.dumps(meta, indent=2) + '\n')
                destination = self.cache / 'generations' / uuid.uuid4().hex
                os.replace(stage, destination)
                changed_image = False
                old_link = self.current_wallpaper.resolve() if self.current_wallpaper.is_symlink() and self.current_wallpaper.is_file() else None
                linked = False
                try:
                    # Preparation precedes presentation: one wallpaper update,
                    # with all colour files already validated and complete.
                    if apply and (restore or reapply or not old or old['wallpaper'] != str(path) or old['wallpaper_hash'] != digest):
                        self.apply_image(path)
                        changed_image = True
                    self.link_wallpaper(path)
                    linked = True
                    self.publish(destination)
                    if reload:
                        for warning in self.reload():
                            print('WARNING: ' + warning, file=sys.stderr)
                    persist(selected)
                except BaseException:
                    if linked:
                        if previous:
                            try:
                                old_link = image_valid(old['wallpaper'])
                            except (OSError, ValueError):
                                old_link = image_valid(self.data / 'wallpapers/min_forest.jpg')
                        if old_link and old_link.is_file():
                            self.link_wallpaper(old_link)
                        else:
                            self.current_wallpaper.unlink(missing_ok=True)
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
                        self.link_wallpaper(path)
                        self.publish(emergency)
                    raise
                self.sync_login_theme(path)
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
            with engine.locked():
                saved = engine.load_state(migrate=True)
                cache = engine.cache_status(saved)
                meta = engine.read() if cache == 'valid' else None
                print('dynamic theming: ' + ('enabled' if saved and saved['enabled'] else 'disabled'))
                print('current wallpaper: ' + str(saved['wallpaper'] or 'none' if saved else 'none'))
                print('wallpaper hash: ' + str(saved['wallpaper_hash'] or 'none' if saved else 'none'))
                print('cache: ' + cache)
                stable = engine.current_wallpaper
                print('wallpaper link: ' + ('valid' if stable.is_symlink() and stable.is_file() else
                                            'invalid' if stable.exists() or stable.is_symlink() else 'missing'))
                if cache == 'invalid':
                    print('cache reason: ' + engine.cache_reason(saved))
                palette = ('dynamic' if meta['source'].startswith('wallust') else 'default') if meta else 'unavailable'
                print('palette: ' + palette)
                if meta:
                    print('palette source: ' + meta['source'])
                    print('last generation: ' + meta['created'])
                print('Wallust version: ' + str(engine.version() or 'absent'))
            return 0
        action = args.action
        wallpaper = Path(args.wallpaper) if args.wallpaper else None
        engine.transact(wallpaper,
                        enabled=False if action == 'disable' else True if action == 'enable' else None,
                        force=action in ('refresh', 'default', 'enable', 'disable'),
                        use_default=action == 'default', apply=action != 'init',
                        reload=action != 'init', restore=action == 'restore', initialize=action == 'init',
                        reapply=action in ('apply', 'default'))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
