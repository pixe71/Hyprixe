import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
from support import source_path, configure_imports, shell_bytes
configure_imports()

spec = importlib.util.spec_from_file_location('apt_build_deps', source_path(ROOT, 'scripts/apt-build-deps.py'))
deps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deps)


class BuildDependencyTests(unittest.TestCase):
    def plan(self, packages, installed, sources, indirect=(), unavailable=()):
        def query(*args):
            if args[0] == 'dpkg-query':
                return installed
            if args[:2] == ('apt-cache', 'depends'):
                return '\n'.join([*packages, *indirect])
            if args[:3] == ('apt-cache', 'show', '--no-all-versions'):
                return '\n\n'.join(f'Package: {name}\nSource: {source}\nVersion: 1.7.0-2'
                                   for name, source in sources.items())
            if args[:2] == ('apt-cache', 'show'):
                name = args[2].split('/')[0]
                if name in unavailable:
                    return ''
                return f'Package: {name}\nSource: {sources[name]}\nVersion: 1.13.1-1~bpo13+1\n'
            self.fail(f'Unexpected metadata query: {args}')
        with patch.object(deps, 'query', side_effect=query), contextlib.redirect_stderr(io.StringIO()):
            return deps.select_packages(packages)

    def test_stable_runtime_keeps_stable_headers(self):
        packages = ['libxkbcommon-dev', 'libxkbregistry-dev', 'libgtkmm-3.0-dev']
        result = self.plan(packages, 'installed\t1.7.0-2\tlibxkbcommon\n', {})
        self.assertEqual(result, packages)

    def test_backports_xkb_runtimes_select_both_matching_headers_only(self):
        packages = ['libxkbcommon-dev', 'libxkbregistry-dev', 'libgtkmm-3.0-dev', 'libjsoncpp-dev']
        sources = {'libxkbcommon-dev': 'libxkbcommon', 'libxkbregistry-dev': 'libxkbcommon',
                   'libgtkmm-3.0-dev': 'gtkmm3.0', 'libjsoncpp-dev': 'libjsoncpp'}
        result = self.plan(packages, 'installed\t1.13.1-1~bpo13+1\tlibxkbcommon\n', sources)
        self.assertEqual(result, ['libxkbcommon-dev/trixie-backports',
                                  'libxkbregistry-dev/trixie-backports',
                                  'libgtkmm-3.0-dev', 'libjsoncpp-dev'])

    def test_indirect_header_dependency_matches_installed_library_family(self):
        sources = {'libgtkmm-3.0-dev': 'gtkmm3.0', 'libwayland-dev': 'wayland',
                   'libxml2-dev': 'libxml2'}
        result = self.plan(['libgtkmm-3.0-dev'],
                           'installed\t1.24.0-1~bpo13+1\twayland\n', sources,
                           indirect=['libwayland-dev', 'libxml2-dev'])
        self.assertEqual(result, ['libgtkmm-3.0-dev', 'libwayland-dev/trixie-backports'])

    def test_unrelated_backport_does_not_promote_headers(self):
        packages = ['libxkbcommon-dev', 'libgtkmm-3.0-dev']
        result = self.plan(packages, 'installed\t1.96.1-1~bpo13+1\trustc\n',
                           {'libxkbcommon-dev': 'libxkbcommon', 'libgtkmm-3.0-dev': 'gtkmm3.0'})
        self.assertEqual(result, packages)

    def test_removed_package_is_not_treated_as_installed_backport(self):
        packages = ['libxkbcommon-dev']
        result = self.plan(packages, 'config-files\t1.13.1-1~bpo13+1\tlibxkbcommon\n', {})
        self.assertEqual(result, packages)

    def test_unavailable_matching_backport_fails_instead_of_falling_back(self):
        with self.assertRaisesRegex(RuntimeError, 'no downgrade will be attempted'):
            self.plan(['libxkbcommon-dev'], 'installed\t1.13.1-1~bpo13+1\tlibxkbcommon\n',
                      {'libxkbcommon-dev': 'libxkbcommon'}, unavailable=['libxkbcommon-dev'])

    def test_metadata_error_is_fatal(self):
        with patch.object(deps, 'query', side_effect=RuntimeError('APT metadata unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'APT metadata unavailable'):
                deps.select_packages(['libxkbcommon-dev'])


if __name__ == '__main__':
    unittest.main()
