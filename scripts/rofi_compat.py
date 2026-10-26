"""Probe Rofi's compiled Wayland capability without requiring a live display."""
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
    sys.exit(0 if has_wayland_support() else 1)
