"""Core/source checks are independent from installed/session theme checks."""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'common/theme'))
from engine import Engine, FILES, defaults, image_valid, render, sha, validate_outputs


@contextmanager
def resolved_config(root=ROOT):
    """Materialize import paths for source parsers without touching the checkout."""
    with tempfile.TemporaryDirectory(prefix='hyprixe-source-theme-') as folder:
        temporary = Path(folder)
        config = temporary / 'config'
        shutil.copytree(root / 'common/config', config)
        colours = temporary / 'theme'
        colours.mkdir()
        for name, text in render(root / 'common/theme', defaults(root / 'common/theme')).items():
            (colours / name).write_text(text)
        for path in config.rglob('*'):
            if path.suffix in ('.rasi', '.conf', '.css'):
                path.write_text(path.read_text().replace('@HYPRIXE_THEME@', str(colours)))
        yield config


def check_source(report, root=ROOT):
    resources = root / 'common/theme'
    try:
        outputs = render(resources, defaults(resources))
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            for name, text in outputs.items():
                (directory / name).write_text(text)
            validate_outputs(directory)
    except (OSError, ValueError) as exc:
        report(False, 'Hyprixe dynamic theme templates valid: ' + str(exc))
    else:
        report(True, 'Hyprixe dynamic theme templates valid (seven colour-only outputs)')
    # Every dynamic import names one managed output; placeholders are resolved
    # once by installation, never by editing source configs at runtime.
    checks = {
        'hypr/waybar/style/Frosted-Glass.css': 'waybar.css',
        'hypr/rofi/wallust/colors-rofi.rasi': 'rofi.rasi',
        'kitty/kitty.conf': 'kitty.conf', 'wlogout/style.css': 'wlogout.css',
        'hypr/hyprlock.conf': 'hyprlock.conf', 'swaync/style.css': 'swaync.css',
    }
    valid = all('@HYPRIXE_THEME@/' + output in (root / 'common/config' / path).read_text()
                for path, output in checks.items())
    valid &= '/hyprixe/theme/current/hyprland.lua' in (root / 'common/config/hypr/UserConfigs/user_decorations.lua').read_text()
    report(valid, 'Component dynamic colour imports resolve through one generation')


def check_installed(report):
    try:
        engine = Engine()
        meta = engine.read()
        report(bool(meta), 'Generated theme palette valid (roles, contrast, checksums)')
        if not meta:
            return
        image = image_valid(meta['wallpaper'])
        report(sha(image) == meta['wallpaper_hash'] and
               (engine.state / 'wallpaper').read_text().strip() == str(image), 'Current wallpaper state valid')
        config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        imports = {'hypr/waybar/style/Frosted-Glass.css': 'waybar.css',
                   'hypr/rofi/wallust/colors-rofi.rasi': 'rofi.rasi',
                   'kitty/kitty.conf': 'kitty.conf', 'wlogout/style.css': 'wlogout.css',
                   'hypr/hyprlock.conf': 'hyprlock.conf', 'swaync/style.css': 'swaync.css'}
        valid = all(str(engine.current / output) in (config / name).read_text() and
                    (engine.current / output).is_file() for name, output in imports.items())
        report(valid, 'Installed component dynamic colour imports resolve')
    except (OSError, ValueError, KeyError) as exc:
        report(False, 'Dynamic theme state: ' + str(exc))
