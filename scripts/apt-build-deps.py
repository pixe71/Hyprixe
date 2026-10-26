"""Select build headers matching installed Debian 13 backports library families.

Only matching development packages opt into trixie-backports. No global target
release or persistent APT pin is used. --simulate runs the real APT resolver.
"""
import argparse
import os
import re
import subprocess
import sys

SUITE = 'trixie-backports'
DEPENDENCIES = {
    'awww': ('build-essential', 'pkg-config', 'libwayland-dev', 'liblz4-dev', 'wayland-protocols'),
    'waybar': ('build-essential', 'meson', 'ninja-build', 'pkg-config',
               'libgtkmm-3.0-dev', 'libjsoncpp-dev', 'libsigc++-2.0-dev', 'libfmt-dev', 'libspdlog-dev',
               'libwayland-dev', 'wayland-protocols', 'libdbusmenu-gtk3-dev', 'libnl-3-dev',
               'libnl-genl-3-dev', 'libpulse-dev', 'libplayerctl-dev', 'libxkbcommon-dev',
               'libxkbregistry-dev', 'libudev-dev', 'libgtk-layer-shell-dev'),
    'rofi': ('build-essential', 'meson', 'ninja-build', 'pkg-config', 'flex', 'bison',
             'libglib2.0-dev', 'libcairo2-dev', 'libpango1.0-dev', 'libgdk-pixbuf-2.0-dev',
             'libxkbcommon-dev', 'libwayland-dev', 'wayland-protocols'),
}


def query(*command):
    result = subprocess.run(command, env=dict(os.environ, LC_ALL='C'),
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed: {result.stderr.strip()}')
    return result.stdout


def records(text):
    for paragraph in re.split(r'\n\s*\n', text.strip()):
        fields = {}
        for line in paragraph.splitlines():
            if line and not line[0].isspace() and ':' in line:
                key, value = line.split(':', 1)
                fields[key] = value.strip()
        if fields:
            yield fields


def select_packages(packages):
    packages = list(dict.fromkeys(packages))
    status = query('dpkg-query', '-W', '-f=${db:Status-Status}\t${Version}\t${source:Package}\n')
    backported = set()
    for line in status.splitlines():
        state, version, source = line.split('\t')
        if state == 'installed' and re.search(r'~bpo13(?:[+.]|$)', version):
            backported.add(source)
    if not backported:
        return packages

    # Include indirect header dependencies (e.g. GTK -> XKB or registry -> XML).
    graph = query('apt-cache', 'depends', '--recurse', '--no-recommends', '--no-suggests',
                  '--no-conflicts', '--no-breaks', '--no-replaces', '--no-enhances', *packages)
    headers = [line for line in graph.splitlines()
               if re.fullmatch(r'[a-z0-9][a-z0-9+.-]*-dev(?::[a-z0-9]+)?', line)]
    candidates = list(dict.fromkeys([*packages, *headers]))
    metadata = query('apt-cache', 'show', '--no-all-versions', *candidates)
    sources = {item['Package']: item.get('Source', item['Package']).split()[0]
               for item in records(metadata) if 'Package' in item}
    selected = {}
    for package in candidates:
        name = package.split(':', 1)[0]
        source = sources.get(name)
        if not name.endswith('-dev') or source not in backported:
            continue
        choice = package + '/' + SUITE
        available = list(records(query('apt-cache', 'show', choice)))
        if not any(item.get('Package') == name and '~bpo13' in item.get('Version', '')
                   and item.get('Source', name).split()[0] == source for item in available):
            raise RuntimeError(f'{choice} unavailable; cannot match installed backports source {source}. '
                               'Refresh the official backports index; no downgrade will be attempted.')
        selected[package] = choice
        print(f'Build dependency: {choice} (installed backports source: {source})', file=sys.stderr)
    return [selected.get(package, package) for package in packages] + [
        choice for package, choice in selected.items() if package not in packages]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=DEPENDENCIES)
    parser.add_argument('--simulate', action='store_true')
    args = parser.parse_args()
    packages = select_packages(DEPENDENCIES[args.component])
    if args.simulate:
        return subprocess.call(['apt-get', '-s', '--no-remove',
                                '-o', 'APT::Get::allow-Downgrades=false', 'install', *packages])
    print('\n'.join(packages))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        print(f'ERROR: build dependencies: {exc}', file=sys.stderr)
        sys.exit(1)
