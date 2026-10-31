"""Run common regressions separately from supported platform integration tests."""
import argparse
from pathlib import Path
import sys
import unittest
from profile_checks import registry

ROOT = Path(__file__).resolve().parents[1]


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def select(tests, profiles, group):
    modules = {module: name for name, data in profiles.items() for module in data.get('tests', [])}
    for test in tests:
        platform = getattr(test, 'PLATFORM', modules.get(test.__class__.__module__))
        if (group == 'common' and platform is None) or group == platform:
            yield test


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('group')
    args = parser.parse_args()
    profiles = registry(ROOT)
    if args.group != 'common' and args.group not in profiles:
        parser.error('Unknown test group')
    if args.group != 'common' and profiles[args.group]['status'] == 'planned':
        print('SKIPPED: planned profile has no implementation: ' + args.group)
        return 0
    tests = flatten(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    chosen = list(select(tests, profiles, args.group))
    if not chosen:
        parser.error('Required test group is empty')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(chosen))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
