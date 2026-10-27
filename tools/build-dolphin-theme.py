#!/usr/bin/env python3
"""Derive Dolphin-only paint from Frosted-Glass; never alter widget geometry."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NAME = 'Frosted-Glass-Dolphin'
COLORS = {
    'window.color': '#203f52', 'base.color': '#1b3a4bd1', 'alt.base.color': '#214454d1',
    'button.color': '#214455', 'light.color': '#6da6b8', 'mid.light.color': '#3e6d80',
    'dark.color': '#102a3b', 'mid.color': '#3b6375', 'highlight.color': '#237e98',
    'inactive.highlight.color': '#286b83', 'text.color': '#e2eff5',
    'window.text.color': '#e2eff5', 'button.text.color': '#e2eff5',
    'disabled.text.color': '#91b1c1', 'tooltip.text.color': '#e6f3f7',
    'highlight.text.color': '#f1fbff', 'link.color': '#62cfda', 'link.visited.color': '#95b9d6',
    'progress.indicator.text.color': '#e8f7fc',
}
SVG_COLORS = {
    '#ffffff': '#203f52', '#012339': '#abcbd8', '#1e4c84': '#237e98', '#2770c0': '#39b8cc',
    '#b74aff': '#6c8fb4', '#a44185': '#6c8fb4', '#dfdfdf': '#426477', '#c1c1c1': '#456a7c',
    '#989898': '#6b95a8', '#5a5a5a': '#b8d2dd', '#343031': '#203e50', '#4285f4': '#4abdcf',
    '#26272a': '#1a3647', '#acb1bc': '#86a9bb', '#5a616e': '#9ebcc9', '#212121': '#163344',
    '#f2f2f2': '#1a3c4c', '#666666': '#7fa6b9', '#b6b6b6': '#456a7c',
}


def main():
    base = ROOT / '.config/Kvantum/Frosted-Glass'
    output = ROOT / '.config/Kvantum' / NAME
    output.mkdir(exist_ok=True)
    section, lines = '', []
    for line in (base / 'Frosted-Glass.kvconfig').read_text().splitlines():
        if line.startswith('['):
            section = line
        if '=' in line:
            key, value = line.split('=', 1)
            if section == '[GeneralColors]' and key in COLORS:
                line = key + '=' + COLORS[key]
            elif key.startswith('text.') and key.endswith('.color'):
                line = key + '=' + ('#91b1c1' if 'disabled' in key else '#e2eff5')
            elif key == 'author':
                line = 'author=Hyprixe, derived from Vince Liuice / KvAdapta by Tsu Jan'
            elif key == 'comment':
                line = 'comment=Dolphin-only blue/cyan translucent paint; original geometry retained'
        lines.append(line)
    (output / (NAME + '.kvconfig')).write_text('\n'.join(lines) + '\n')
    svg = (base / 'Frosted-Glass.svg').read_text()
    svg = re.sub(r'#[0-9a-fA-F]{6}\b', lambda m: SVG_COLORS.get(m[0].lower(), m[0]), svg)
    # Paint only these existing SVG interiors; dimensions, paths and IDs stay put.
    paints = {'window-normal': ('#203f52', '.78'), 'dock-normal': ('#102b3b', '.38'),
              'menubar-normal': ('#153244', '.40'), 'menu-normal': ('#102f40', '.94'),
              'tooltip-normal': ('#102f40', '.96'), 'itemview-toggled': ('#237e98', '.88'),
              'itemview-focused': ('#43bdd0', '.24')}
    root = ET.fromstring(svg)
    for element in root.iter():
        if element.get('id') not in paints:
            continue
        color, alpha = paints[element.get('id')]
        style = dict(part.split(':', 1) for part in element.get('style', '').split(';') if ':' in part)
        style.update({'fill': color, 'fill-opacity': alpha, 'opacity': '1'})
        old = element.get('style', '')
        new = ';'.join(k + ':' + v for k, v in style.items())
        # Preserve the source XML formatting/namespaces, not an ET reserialization.
        pattern = r'(<[^>]*\bid="' + re.escape(element.get('id')) + r'"[^>]*\bstyle=")' + re.escape(old) + '"'
        svg, count = re.subn(pattern, lambda m: m[1] + new + '"', svg)
        assert count == 1, element.get('id')
    (output / (NAME + '.svg')).write_text(svg)


if __name__ == '__main__':
    main()
