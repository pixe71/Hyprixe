"""Shared Hyprland eligibility policy; eligibility is not release validation.

The minimum has a technical basis: Hyprixe uses the 0.55.2 Lua API. There is
no speculative upper bound. Other release numbers must pass the real config,
API and session checks and remain unvalidated until evidence is recorded.
"""
from dataclasses import dataclass
import re

MINIMUM = (0, 55, 2)
REVIEWED_RELEASES = frozenset({(0, 55, 2), (0, 56, 2)})


def format_version(version):
    return '.'.join(map(str, version))


@dataclass(frozen=True)
class Assessment:
    allowed: bool
    reviewed: bool
    message: str

    @property
    def warning(self):
        if self.allowed and not self.reviewed:
            return ('This Hyprland release/build is not a reviewed Hyprixe reference; '
                    'acceptance is provisional. Run configuration/API/session checks '
                    'and physical acceptance tests before relying on it.')
        return ''


def assess(output, returncode=0):
    if returncode:
        return Assessment(False, False, 'Cannot query the Hyprland version (command failed).')
    match = re.search(r'\bHyprland\s+v?(\d+)\.(\d+)\.(\d+)'
                      r'(?P<suffix>[-+~][\w.+~-]*)?(?=\s|$)', output, re.IGNORECASE)
    if not match:
        return Assessment(False, False, 'Cannot identify a Hyprland release in version output.')
    version = tuple(map(int, match.group(1, 2, 3)))
    label = format_version(version) + (match['suffix'] or '')
    suffix = match['suffix'] or ''
    prerelease = bool(re.match(r'[-~](?:alpha|beta|rc|pre|dev)', suffix, re.IGNORECASE))
    if version < MINIMUM or (version == MINIMUM and prerelease):
        return Assessment(False, False, f'Hyprland {label} is below the required Lua API minimum '
                          f'{format_version(MINIMUM)}.')
    # Debian's +ds repacking does not imply a prerelease. Development/RC builds
    # using a reviewed base number must still carry the provisional warning.
    reviewed = version in REVIEWED_RELEASES and (not suffix or
               bool(re.fullmatch(r'\+ds(?:[.\d]*)(?:-\d+(?:~bpo\d+\+\d+)?)?', suffix)))
    state = 'reviewed release number' if reviewed else 'eligible, unreviewed release/build'
    return Assessment(True, reviewed, f'Hyprland {label}: {state}; minimum '
                      f'{format_version(MINIMUM)}, no speculative upper bound.')
