"""Probe Rofi's compiled Wayland capability without requiring a live display."""

from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "scripts"))
from source_layout import ROOT as REPOSITORY_ROOT, source_path, configure_imports, shell_bytes
configure_imports()
import os
import re
import shutil
import subprocess
import sys


def has_wayland_support(executable=None):
    executable = executable or shutil.which('rofi')
    if not executable:
        return False
    probe = dict(os.environ, WAYLAND_DISPLAY='hyprixe-capability-probe', DISPLAY='')
    try:
        info = subprocess.run([str(executable), '-info'], env=probe,
                              capture_output=True, text=True, timeout=10)
        version = subprocess.run([str(executable), '-version'], env=probe,
                                 capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    output = '\n'.join((info.stdout, info.stderr, version.stdout, version.stderr))
    return bool(re.search(r'wayland\s+enabled|wayland:.*selected|Version[^\n]*wayland',
                          output, re.I))


if __name__ == '__main__':
    import argparse
    from rofi_launcher import has_launcher_actions, has_launcher_cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launcher', action='store_true', help='also require launcher buttons and preview rendering')
    args = parser.parse_args()
    sys.exit(0 if has_wayland_support() and
             (not args.launcher or (has_launcher_actions(shutil.which('rofi')) and
                                    has_launcher_cover(shutil.which('rofi')))) else 1)
