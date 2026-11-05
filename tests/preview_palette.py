"""Offline palette contact sheet. Never applies a theme or writes user state."""
import argparse
import base64
from html import escape
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from test_palette_refinement import SWATCHES, fixture, raw, engine, RESOURCES


def rows(root, real_wallust, fixtures):
    base = engine.defaults(RESOURCES)
    runtime = engine.Engine(RESOURCES)
    if real_wallust and runtime.version() != engine.WALLUST_VERSION:
        raise ValueError('This preview requires Wallust ' + engine.WALLUST_VERSION)
    yield 'min_forest (unchanged reference)', base, None, None, 'historical Frosted Glass'
    for name, colors in SWATCHES.items():
        image = fixture(fixtures / (name + '.png'), colors)
        extracted, source = raw(colors), 'synthetic raw palette (transformation only)'
        if real_wallust:
            stage = root / name
            stage.mkdir()
            try:
                extracted = runtime.extract(image, stage)
            except ValueError as exc:
                yield name, base, image, None, 'Frosted Glass fallback: ' + str(exc)
                continue
            source = 'Wallust ' + engine.WALLUST_VERSION
        yield name, engine.normalize(extracted, base), image, extracted, source


def html_report(data):
    sections = []
    for name, p, image, extracted, source in data:
        thumbnail = ('<img alt="Synthetic wallpaper" src="data:image/png;base64,' +
                     base64.b64encode(image.read_bytes()).decode() + '">' if image else '')
        raw_swatches = ''.join(f'<i title="{c}" style="background:{c}"></i>' for c in extracted['colors']) if extracted else ''
        swatches = ''.join(f'<div style="background:{color};color:{p["background"] if engine.luminance(color) > .3 else p["foreground"]}">'
                           f'{role}<br><code>{color}</code></div>' for role, color in p.items())
        sections.append(f'''<section style="background:{p['background']};color:{p['foreground']}">
<h2>{escape(name)}</h2><p>{escape(source)}</p>{thumbnail}<div class="raw">{raw_swatches}</div>
<div class="swatches">{swatches}</div>
<p class="example" style="background:{p['surface']}">Normal text <span style="color:{p['foreground_muted']}"> · Secondary text</span>
<b style="background:{p['selection']};color:{p['foreground']}">Rofi selected</b>
<b style="background:{p['workspace']};color:{p['foreground']}">Workspace 1</b>
<b style="background:{p['accent']};color:{p['background']}">Kitty / SDDM selection</b>
<span style="color:{p['error']}">Error</span></p>
<small>Text/surface_alt {engine.contrast(p['foreground'], p['surface_alt']):.2f}:1 ·
Muted/surface_alt {engine.contrast(p['foreground_muted'], p['surface_alt']):.2f}:1 ·
Selection text {engine.contrast(p['foreground'], p['selection']):.2f}:1 ·
Accent distance ΔE OK {engine.distance(p['accent'], p['accent_alt']):.3f}</small></section>''')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Hyprixe palette review</title>
<style>body{background:#10141a;color:#e6edf3;font:15px system-ui;margin:24px}h1,h2{font-weight:600}
section{border:1px solid #59616b;border-radius:16px;padding:20px;margin:20px 0}section img{width:256px;image-rendering:pixelated}
.raw{display:flex;margin:12px 0}.raw i{width:32px;height:24px}.swatches{display:flex;flex-wrap:wrap;gap:6px}
.swatches div{padding:12px;width:145px;border:1px solid #737982;border-radius:8px}code{font-size:14px}
.example{padding:18px;border-radius:12px;line-height:3}.example b{padding:8px;border-radius:8px;font-weight:500}</style>
<h1>Hyprixe · Frosted Glass palette review</h1><p>Opaque semantic swatches, not a screenshot of the compositor.
Layouts, opacity, blur and wallpaper propagation are unchanged. No user state is modified.</p>''' + ''.join(sections) + '</html>\n'


def png_report(data, path):
    from PIL import Image, ImageDraw, ImageFont
    canvas = Image.new('RGB', (1440, len(data)*200 + 64), '#10141a')
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 16)
        small = ImageFont.truetype('DejaVuSans.ttf', 13)
    except OSError:
        font = small = ImageFont.load_default()
    draw.text((24, 20), 'Hyprixe palette review: semantic colours, unchanged opacity/layout', font=font, fill='#e6edf3')
    for index, (name, p, _, _, source) in enumerate(data):
        y = 64 + index*200
        draw.rounded_rectangle((12, y, 1428, y+190), radius=12, fill=p['background'])
        draw.text((28, y+10), name + ' · ' + source.split(':')[0], font=font, fill=p['foreground'])
        for column, (role, color) in enumerate(p.items()):
            x = 28 + column*91
            draw.rounded_rectangle((x, y+42, x+84, y+96), radius=6, fill=color, outline=p['border'])
            draw.text((x, y+101), role.replace('foreground', 'fg').replace('secondary', 'sec'), font=small, fill=p['foreground_muted'])
            draw.text((x, y+120), color, font=small, fill=p['foreground_muted'])
        for column, (label, bg, fg) in enumerate((('Normal / muted', p['surface'], p['foreground_muted']),
                                                   ('Selected', p['selection'], p['foreground']),
                                                   ('Workspace', p['workspace'], p['foreground']),
                                                   ('Pressed / terminal selection', p['accent'], p['background']))):
            x = 28 + column*344
            draw.rounded_rectangle((x, y+149, x+330, y+180), radius=6, fill=bg)
            draw.text((x+10, y+154), label, font=small, fill=fg)
    canvas.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Standalone HTML report')
    parser.add_argument('--png', type=Path, help='Optional contact sheet')
    parser.add_argument('--fixtures', type=Path, help='Retain tiny synthetic wallpapers for desktop testing')
    parser.add_argument('--wallust', action='store_true', help='Use actual pinned extraction, including its real fallback')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hyprixe palette preview ') as folder:
        root = Path(folder)
        fixtures = args.fixtures or root / 'fixtures'
        fixtures.mkdir(parents=True, exist_ok=True)
        env = {f'XDG_{name}_HOME': str(root / name.lower()) for name in ('CACHE', 'STATE', 'DATA')}
        with patch.dict(os.environ, env):
            data = list(rows(root, args.wallust, fixtures))
        args.output.write_text(html_report(data), encoding='utf-8')
        if args.png:
            png_report(data, args.png)
        print(args.output)
        for name, palette, _, _, source in data:
            print(name + ': ' + source + ' · accent ' + palette['accent'] + ' / ' + palette['accent_alt'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
