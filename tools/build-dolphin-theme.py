#!/usr/bin/env python3
"""Derive Dolphin-only paint from Frosted-Glass; never alter widget geometry."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NAME = 'Frosted-Glass-Dolphin'
COLORS = {
    'window.color': '#e7e9e8', 'base.color': '#e9ecead1', 'alt.base.color': '#dde2e0d1',
    'button.color': '#e0e4e2', 'light.color': '#f0f2f0', 'mid.light.color': '#d3dbd7',
    'dark.color': '#9aa8a8', 'mid.color': '#bdc8c4', 'highlight.color': '#c4dce2',
    'inactive.highlight.color': '#d4e0e2', 'text.color': '#2d3437',
    'window.text.color': '#2d3437', 'button.text.color': '#2d3437',
    'disabled.text.color': '#697477', 'tooltip.text.color': '#30393c',
    'highlight.text.color': '#263d44', 'link.color': '#528a98', 'link.visited.color': '#668994',
    'progress.indicator.text.color': '#263d44',
}
SVG_COLORS = {
    '#ffffff': '#e7e9e8', '#012339': '#3e494d', '#1e4c84': '#c4dce2', '#2770c0': '#709ca6',
    '#b74aff': '#91acb0', '#a44185': '#91acb0', '#dfdfdf': '#d9dfdc', '#c1c1c1': '#c6cecb',
    '#989898': '#909e9e', '#5a5a5a': '#536367', '#343031': '#d9dfdc', '#4285f4': '#6c9da6',
    '#26272a': '#dce2df', '#acb1bc': '#adbab9', '#5a616e': '#697879', '#212121': '#cad2cf',
    '#f2f2f2': '#e7ebe8', '#666666': '#7a8a8a', '#b6b6b6': '#c4cecb',
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
            elif key == 'highlight.text.color':
                line = key + '=#263d44'
            elif key.startswith('text.') and key.endswith('.color'):
                line = key + '=' + ('#697477' if 'disabled' in key else '#2d3437')
            elif key == 'author':
                line = 'author=Hyprixe, derived from Vince Liuice / KvAdapta by Tsu Jan'
            elif key == 'comment':
                line = 'comment=Dolphin-only neutral light glass paint; existing alpha and geometry retained'
        lines.append(line)
    (output / (NAME + '.kvconfig')).write_text('\n'.join(lines) + '\n')
    svg = (base / 'Frosted-Glass.svg').read_text()
    svg = re.sub(r'#[0-9a-fA-F]{6}\b', lambda m: SVG_COLORS.get(m[0].lower(), m[0]), svg)
    # Paint only these existing SVG interiors; dimensions, paths and IDs stay put.
    paints = {'window-normal': ('#e7e9e8', '.78'), 'dock-normal': ('#d5d9d8', '.38'),
              'menubar-normal': ('#dde1df', '.40'), 'menu-normal': ('#e8ebe9', '.94'),
              'tooltip-normal': ('#edf0ee', '.96'), 'itemview-toggled': ('#c4dce2', '.88'),
              'itemview-focused': ('#cadbdd', '.24')}
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
