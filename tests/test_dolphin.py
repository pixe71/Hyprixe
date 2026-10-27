import base64
import contextlib
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import deploy
import dolphin_interface
from dolphin_config import THEME, THEME_FILES, VIEW_XATTR, SCHEME_NAME, read_ini
from dolphin_checks import check_source, check_installed, check_session


class DolphinDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe Dolphin ')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'desktop user'
        self.home.mkdir()
        self.roots = {key: self.home / name for key, name in
                      (('config', 'settings with spaces'), ('data', 'application data'), ('state', 'session state'))}
        env = patch.dict(os.environ, {'HOME': str(self.home),
            **{'XDG_' + key.upper() + '_HOME': str(path) for key, path in self.roots.items()}})
        env.start(); self.addCleanup(env.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__(); self.addCleanup(output.__exit__, None, None, None)

    def install(self, **kwargs):
        return deploy.install(self.home, self.roots, 'native', dolphin_only=True, **kwargs)

    def write(self, key, name, data):
        path = self.roots[key] / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path

    def xattr(self, path, value):
        path.mkdir(parents=True, exist_ok=True)
        try:
            os.setxattr(path, VIEW_XATTR, value)
        except OSError as exc:
            if exc.errno in (errno.ENOTSUP, errno.EOPNOTSUPP):
                self.skipTest('Filesystem does not support view-property xattrs')
            raise

    def test_style_only_changes_five_paint_files_never_creates_layout(self):
        backup = self.install()
        manifest = deploy.read_manifest(backup)
        self.assertEqual(manifest['scope'], 'dolphin-style')
        self.assertEqual(len(manifest['files']), 5)
        self.assertEqual(read_ini(self.roots['config'] / 'dolphinrc').sections(), ['UiSettings'])
        self.assertFalse((self.roots['data'] / 'kxmlgui5').exists())
        self.assertNotIn('dolphin_view_xattr', manifest)
        self.assertIsNone(self.install())

    def test_interface_is_byte_identical_except_native_color_scheme_selection(self):
        files = [self.write(key, name, '[General]\nPersonal=' + name + '\n') for key, name in dolphin_interface.FILES]
        files += [self.write('data', 'user-places.xbel', '<not-even-parsed-by-paint>'),
                  self.write('config', 'hypr/profile.lua', 'personal profile'),
                  self.write('config', 'kdeglobals', 'existing Qt integration')]
        directory = self.roots['data'] / 'dolphin/view_properties/global'
        self.xattr(directory, b'personal view')
        before = {p: p.read_bytes() for p in files}
        backup = self.install()
        styled = before.copy()
        rc = self.roots['config'] / 'dolphinrc'
        styled[rc] = deploy.merge_ini(before[rc].decode(), {'UiSettings': {'ColorScheme': SCHEME_NAME}}).encode()
        self.assertEqual({p: p.read_bytes() for p in files}, styled)
        self.assertEqual(os.getxattr(directory, VIEW_XATTR), b'personal view')
        deploy.restore(backup, self.home)
        self.assertEqual({p: p.read_bytes() for p in files}, before)
        self.assertEqual(os.getxattr(directory, VIEW_XATTR), b'personal view')

    def test_global_theme_and_other_application_associations_are_preserved(self):
        master = self.write('config', 'Kvantum/kvantum.kvconfig',
            '[General]\ntheme=MyOtherTheme\n[Applications]\nOld=Dolphin,okular\nAnother=kate\n')
        backup = self.install()
        settings = read_ini(master)
        self.assertEqual(settings['General']['theme'], 'MyOtherTheme')
        self.assertEqual(dict(settings['Applications']), {'Old': 'okular', 'Another': 'kate', THEME: 'dolphin'})
        self.assertIsNone(self.install())
        deploy.restore(backup, self.home)
        self.assertIn('Old=Dolphin,okular', master.read_text())

    def test_full_install_preserves_existing_interface(self):
        rc = self.write('config', 'dolphinrc', '[General]\nPersonal=true\n')
        toolbar = self.write('data', 'kxmlgui5/dolphin/dolphinui.rc', '<personal/>')
        deploy.install(self.home, self.roots, 'native')
        self.assertEqual(rc.read_text(), '[General]\nPersonal=true\n\n[UiSettings]\nColorScheme=' + SCHEME_NAME + '\n')
        self.assertEqual(toolbar.read_text(), '<personal/>')
        self.assertFalse((self.roots['state'] / 'dolphinstaterc').exists())

    def test_fresh_full_install_seeds_exact_git_baseline_without_view_preset(self):
        deploy.install(self.home, self.roots, 'native')
        for root, path, source in (
            ('config', 'dolphinrc', '.config/dolphinrc'),
            ('data', 'kxmlgui5/dolphin/dolphinui.rc', '.local/share/kxmlgui5/dolphin/dolphinui.rc')):
            expected = (ROOT / source).read_bytes()
            if root == 'config':
                expected = deploy.merge_ini(expected.decode(), {'UiSettings': {'ColorScheme': SCHEME_NAME}}).encode()
            self.assertEqual((self.roots[root] / path).read_bytes(), expected)
        self.assertFalse((self.roots['data'] / 'dolphin/view_properties/global/.directory').exists())

    def test_dry_run_creates_nothing(self):
        self.install(dry=True)
        self.assertEqual(list(self.home.iterdir()), [])

    def legacy(self, include_unrelated=False):
        """Reproduce the rejected deployment using its actual tracked toolbar."""
        bad_toolbar = b'rejected toolbar fixture'
        self.fixture_repo = self.home / 'fixture repository'
        spec = json.loads((ROOT / 'dolphin/interface-baseline.json').read_text())
        import hashlib
        spec['bad_toolbar_sha256'] = [hashlib.sha256(bad_toolbar).hexdigest()]
        spec_path = self.fixture_repo / 'dolphin/interface-baseline.json'
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(json.dumps(spec))
        self.originals = {}
        content = {}
        for key, name in dolphin_interface.FILES:
            path = self.write(key, name, '[General]\nOriginal=' + name + '\n')
            self.originals[path] = path.read_bytes()
            content[path] = (bad_toolbar if name.endswith('dolphinui.rc') else b'rejected layout', 0o644)
        if include_unrelated:
            content[self.write('config', 'hypr/waybar/configs/Frosted-Glass', 'old Waybar')] = (b'intermediate Waybar', 0o644)
        directory = self.roots['data'] / 'dolphin/view_properties/global'
        self.xattr(directory, b'original attribute')
        original = deploy.install(self.home, self.roots, 'native', custom_files=content, scope='legacy-fixture')
        self.xattr(directory, b'rejected view')
        return original

    def migration(self, **kw):
        return dolphin_interface.plan(getattr(self, 'fixture_repo', ROOT), self.roots, self.home,
                                     deploy.read_manifest, deploy.digest, deploy.guard, **kw)

    def apply_migration(self):
        files, attribute = self.migration()
        return deploy.install(self.home, self.roots, 'native', custom_files=files,
                              view_xattr_after=attribute, scope='dolphin-interface')

    def test_migration_restores_exact_original_interface_not_other_desktop_changes(self):
        self.legacy(include_unrelated=True)
        waybar = self.roots['config'] / 'hypr/waybar/configs/Frosted-Glass'
        waybar.write_text('newer working Waybar')
        migration = self.apply_migration()
        self.assertEqual({p: p.read_bytes() for p in self.originals}, self.originals)
        self.assertEqual(waybar.read_text(), 'newer working Waybar')
        self.assertEqual(os.getxattr(self.roots['data'] / 'dolphin/view_properties/global', VIEW_XATTR), b'original attribute')
        self.assertEqual(self.migration(), ({}, None))
        paint = self.install()
        deploy.restore(paint, self.home)
        self.assertEqual({p: p.read_bytes() for p in self.originals}, self.originals)
        deploy.restore(migration, self.home)
        self.assertIn('rejected layout', (self.roots['config'] / 'dolphinrc').read_text())
        self.assertFalse((self.roots['state'] / dolphin_interface.MARKER).exists())

    def test_migration_no_backup_fails_without_guessing_interface(self):
        with self.assertRaisesRegex(ValueError, 'No intact'):
            self.migration()
        self.assertEqual(list(self.home.iterdir()), [])

    def test_corrupt_original_aborts_before_any_write(self):
        original = self.legacy()
        manifest = deploy.read_manifest(original)
        first = manifest['files'][0]
        (original / 'files' / first['backup']).write_bytes(b'corrupt')
        current = {p: p.read_bytes() for p in self.originals}
        with self.assertRaisesRegex(ValueError, 'corrupt'):
            self.migration()
        self.assertEqual({p: p.read_bytes() for p in self.originals}, current)
        self.assertFalse((self.roots['state'] / dolphin_interface.MARKER).exists())

    def test_migration_dry_run_creates_no_transaction(self):
        self.legacy()
        files, attribute = self.migration()
        before = {p: p.read_bytes() for p in self.originals}
        deploy.install(self.home, self.roots, 'native', dry=True, custom_files=files, view_xattr_after=attribute)
        self.assertEqual({p: p.read_bytes() for p in self.originals}, before)
        self.assertFalse((self.roots['state'] / dolphin_interface.MARKER).exists())

    def test_migration_invalid_backup_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'backup ID'):
            self.migration(backup_id='../escape')

    def test_migration_removes_only_previously_absent_view_file_and_attribute(self):
        props = self.roots['data'] / 'dolphin/view_properties/global/.directory'
        toolbar = self.write('data', 'kxmlgui5/dolphin/dolphinui.rc', '<original/>')
        import hashlib
        spec = json.loads((ROOT / 'dolphin/interface-baseline.json').read_text())
        spec['bad_toolbar_sha256'] = [hashlib.sha256(b'bad toolbar').hexdigest()]
        self.fixture_repo = self.home / 'fixture repository'
        path = self.fixture_repo / 'dolphin/interface-baseline.json'
        path.parent.mkdir(parents=True); path.write_text(json.dumps(spec))
        deploy.install(self.home, self.roots, 'native', custom_files={
            toolbar: (b'bad toolbar', 0o644), props: (b'rejected view file', 0o644)}, scope='legacy')
        self.xattr(props.parent, b'rejected migrated attribute')
        os.setxattr(props.parent, 'user.hyprixe-unrelated', b'keep')
        self.apply_migration()
        self.assertFalse(props.exists())
        with self.assertRaises(OSError):
            os.getxattr(props.parent, VIEW_XATTR)
        self.assertEqual(os.getxattr(props.parent, 'user.hyprixe-unrelated'), b'keep')
        self.assertEqual(toolbar.read_bytes(), b'<original/>')

    def test_failed_migration_rolls_back_interface_and_keeps_original_attribute(self):
        self.legacy()
        before = {p: p.read_bytes() for p in self.originals}
        real_atomic = deploy.atomic
        def fail_marker(path, *args):
            if str(path).endswith(dolphin_interface.MARKER):
                raise OSError('fixture disk failure')
            return real_atomic(path, *args)
        with patch('deploy.atomic', side_effect=fail_marker):
            with self.assertRaisesRegex(OSError, 'fixture disk failure'):
                self.apply_migration()
        self.assertEqual({p: p.read_bytes() for p in self.originals}, before)
        self.assertEqual(os.getxattr(self.roots['data'] / 'dolphin/view_properties/global', VIEW_XATTR), b'rejected view')

    def test_bookmark_reversion_keeps_new_bookmarks_and_unrelated_groups(self):
        old = b'<xbel><info><metadata owner="http://www.kde.org"><GroupState-Devices-IsHidden>true</GroupState-Devices-IsHidden></metadata></info></xbel>'
        now = b'<xbel><info><metadata owner="http://www.kde.org"><GroupState-Devices-IsHidden>false</GroupState-Devices-IsHidden><GroupState-Remote-IsHidden>true</GroupState-Remote-IsHidden></metadata></info><bookmark href="file:///new"/></xbel>'
        root = ET.fromstring(dolphin_interface.bookmark_flags(now, old))
        self.assertEqual(root.find('bookmark').get('href'), 'file:///new')
        self.assertEqual(root.findtext('info/metadata/GroupState-Devices-IsHidden'), 'true')
        self.assertEqual(root.findtext('info/metadata/GroupState-Remote-IsHidden'), 'true')

    def test_legacy_restore_saves_native_dolphin_changes_and_xattr(self):
        original = self.legacy()
        rc = self.roots['config'] / 'dolphinrc'; rc.write_text('runtime edit')
        with self.assertRaisesRegex(ValueError, 'Nothing restored'):
            deploy.restore(original, self.home)
        deploy.restore(original, self.home, save_dolphin_changes=True)
        self.assertEqual({p: p.read_bytes() for p in self.originals}, self.originals)
        saved = next(original.glob('preserved-dolphin-*'))
        metadata = json.loads((saved / 'manifest.json').read_text())
        self.assertEqual(base64.b64decode(metadata['view_xattr']['value']), b'rejected view')

    def test_shared_kvantum_master_edits_cannot_be_overwritten_by_save_option(self):
        backup = self.install()
        master = self.roots['config'] / 'Kvantum/kvantum.kvconfig'
        master.write_text('personal global theme change')
        with self.assertRaisesRegex(ValueError, 'Nothing restored'):
            deploy.restore(backup, self.home, save_dolphin_changes=True)
        self.assertEqual(master.read_text(), 'personal global theme change')

    def test_installed_check_does_not_enforce_interface_and_detects_fusion(self):
        self.install()
        self.write('config', 'dolphinrc', '[General]\nViewMode=anything the user wants\n[UiSettings]\nColorScheme=' + SCHEME_NAME + '\n')
        results = []
        check_installed(lambda ok, label: results.append((ok, label)))
        self.assertTrue(all(ok for ok, _ in results), results)
        self.write('config', 'qt6ct/qt6ct.conf', '[Appearance]\nstyle=Fusion\n')
        results = []
        check_installed(lambda ok, label: results.append((ok, label)))
        self.assertTrue(any(not ok for ok, _ in results))

    def test_style_restore_does_not_touch_later_personal_interface_changes(self):
        backup = self.install()
        rc = self.write('config', 'dolphinrc', '[General]\nUserChanged=true\n[UiSettings]\nColorScheme=' + SCHEME_NAME + '\n')
        deploy.restore(backup, self.home)
        self.assertIn('UserChanged=true', rc.read_text())
        self.assertNotIn('ColorScheme=', rc.read_text())

    def test_style_restore_rejects_a_later_manual_color_change(self):
        backup = self.install()
        rc = self.roots['config'] / 'dolphinrc'
        rc.write_text('[UiSettings]\nColorScheme=My chosen theme\n')
        with self.assertRaisesRegex(ValueError, 'ColorScheme changed'):
            deploy.restore(backup, self.home, save_dolphin_changes=True)
        self.assertIn('My chosen theme', rc.read_text())

    def test_marker_prevents_a_second_rollback_of_personal_interface_edits(self):
        self.legacy()
        self.apply_migration()
        rc = self.roots['config'] / 'dolphinrc'
        rc.write_text('[General]\nMyLaterInterface=true\n')
        self.assertEqual(self.migration(), ({}, None))
        self.assertIn('MyLaterInterface=true', rc.read_text())


class DolphinChecksTests(unittest.TestCase):
    def test_component_dependencies_are_also_in_full_install_manifest(self):
        def packages(path):
            return {line.split('#', 1)[0].strip() for line in path.read_text().splitlines()} - {''}
        component = packages(ROOT / 'packages-dolphin.txt')
        self.assertTrue({'dolphin', 'kio-extras', 'udisks2', 'qt6-style-kvantum'} <= component)
        self.assertTrue(component <= packages(ROOT / 'packages.txt'))

    def test_kconfig_geometry_keys_and_headerless_baseline_parse(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state'
            path.write_text('MenuBar=Disabled\n[State]\n1920x1080 screen: Width=1280\n1920x1080 screen: Height=800\n')
            parsed = read_ini(path)
            self.assertEqual(parsed['State']['1920x1080 screen: Width'], '1280')
            self.assertEqual(parsed['State']['1920x1080 screen: Height'], '800')
            self.assertEqual(parsed['__root__']['MenuBar'], 'Disabled')

    def test_source_contract(self):
        results = []
        check_source(lambda ok, label: results.append((ok, label)), ROOT)
        self.assertTrue(all(ok for ok, _ in results), results)

    def test_missing_source_files_report_failures_without_traceback(self):
        results = []
        with tempfile.TemporaryDirectory() as temp:
            check_source(lambda ok, label: results.append((ok, label)), Path(temp))
        self.assertEqual(len(results), 3)
        self.assertFalse(any(ok for ok, _ in results))

    def test_svg_geometry_is_identical_to_original_theme(self):
        def geometry(path):
            tree = ET.parse(path)
            for element in tree.iter():
                for name in list(element.attrib):
                    if element.attrib[name].startswith('#') or name in ('fill', 'stroke', 'opacity', 'fill-opacity', 'stroke-opacity', 'stop-color'):
                        del element.attrib[name]
                    elif name == 'style':
                        styles = [part for part in element.attrib[name].split(';') if ':' in part
                                  and part.split(':', 1)[0] not in ('fill', 'fill-opacity', 'stroke', 'stroke-opacity', 'opacity', 'stop-color', 'stop-opacity')]
                        element.attrib[name] = ';'.join(styles)
            return ET.tostring(tree.getroot())
        self.assertEqual(geometry(ROOT / '.config/Kvantum/Frosted-Glass/Frosted-Glass.svg'),
                         geometry(ROOT / '.config' / THEME_FILES[1]))

    def test_kvantum_geometry_options_are_unchanged(self):
        old = read_ini(ROOT / '.config/Kvantum/Frosted-Glass/Frosted-Glass.kvconfig')
        new = read_ini(ROOT / '.config' / THEME_FILES[0])
        for section in old.sections():
            for key, value in old.items(section):
                if section != 'GeneralColors' and not key.endswith('.color') and key not in ('author', 'comment'):
                    self.assertEqual(new[section][key], value, (section, key))

    def test_light_palette_preserves_all_existing_svg_geometry_and_alpha(self):
        # Frozen from the visually accepted blue variant in 0a92888 after
        # masking RGB colors only. Any opacity, path or size change must fail.
        svg = (ROOT / '.config' / THEME_FILES[1]).read_text()
        without_rgb = re.sub(r'#[0-9a-fA-F]{6}\b', '#COLOR', svg)
        self.assertEqual(hashlib.sha256(without_rgb.encode()).hexdigest(),
                         'b0506b92b5149510aa8e0a847019ccbf3a4a4b15ef3ab05a19fd1b6191a9228d')
        palette = read_ini(ROOT / '.config' / THEME_FILES[0])['GeneralColors']
        self.assertTrue(all(palette[key].endswith('d1') for key in ('base.color', 'alt.base.color')))

    def test_running_dolphin_is_refused_without_killing_it(self):
        from dolphin_config import ensure_closed
        with patch('dolphin_config.shutil.which', return_value='/bin/pgrep'), \
             patch('dolphin_config.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as run:
            with self.assertRaisesRegex(ValueError, 'Close all Dolphin'):
                ensure_closed()
        self.assertEqual(run.call_args.args[0], ['pgrep', '-u', str(os.getuid()), '-x', 'dolphin'])

    def test_session_inspects_manager_blur_and_actual_dolphin_override(self):
        replies = [subprocess.CompletedProcess([], 0, 'QT_STYLE_OVERRIDE=kvantum\n', ''),
                   subprocess.CompletedProcess([], 0, '{"int":1}', ''),
                   subprocess.CompletedProcess([], 0, '123\n', '')]
        results = []
        with patch('dolphin_checks.subprocess.run', side_effect=replies), \
             patch('dolphin_checks.Path.read_bytes', return_value=b'HOME=private\0QT_STYLE_OVERRIDE=kvantum\0'):
            check_session(lambda ok, label: results.append((ok, label)))
        self.assertEqual(len(results), 3)
        self.assertTrue(all(ok for ok, _ in results), results)
        self.assertFalse(any('private' in label for _, label in results))

    def test_session_rejects_missing_environment_and_disabled_blur(self):
        replies = [subprocess.CompletedProcess([], 0, 'QT_STYLE_OVERRIDE=Fusion\n', ''),
                   subprocess.CompletedProcess([], 0, '{"int":0}', ''),
                   subprocess.CompletedProcess([], 1, '', '')]
        results = []
        with patch('dolphin_checks.subprocess.run', side_effect=replies):
            check_session(lambda ok, label: results.append((ok, label)))
        self.assertFalse(any(ok for ok, _ in results))


@unittest.skipUnless(os.geteuid() == 0 and shutil.which('setpriv'), 'root/setpriv needed for unprivileged installer fixture')
class DolphinInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe Dolphin installer ')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        python = '''#!/usr/bin/python3
import os,pathlib,sys
if pathlib.Path(sys.argv[1]).name=='dolphin_checks.py':
 if not (pathlib.Path(os.environ['HOME'])/'dependencies-ready').exists():
  print('ERROR: fixture missing preview dependency',file=sys.stderr);sys.exit(1)
 print('PASS: fixture component dependencies');sys.exit(0)
os.execv('/usr/bin/python3',['python3']+sys.argv[1:])
'''
        sudo = '''#!/usr/bin/python3
import json,os,pathlib,sys
home=pathlib.Path(os.environ['HOME'])
with (home/'apt-calls').open('a') as out:out.write(json.dumps(sys.argv[1:])+'\\n')
assert sys.argv[1]=='apt-get',sys.argv
if os.environ.get('MOCK_APT_FAILURE'):sys.exit(17)
if sys.argv[2]=='install':(home/'dependencies-ready').touch()
'''
        for name, code in (('python3', python), ('sudo', sudo), ('pgrep', '#!/bin/sh\nexit 1\n')):
            path = self.bin / name
            path.write_text(code)
            path.chmod(0o755)
        for path in [self.home, *self.home.rglob('*')]:
            os.chown(path, 65534, 65534)
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin) + ':/usr/bin:/bin',
                        XDG_CONFIG_HOME=str(self.home / '.config'), XDG_DATA_HOME=str(self.home / '.local/share'),
                        XDG_STATE_HOME=str(self.home / '.local/state'), PYTHONDONTWRITEBYTECODE='1')

    def run_installer(self, *args):
        return subprocess.run(['setpriv', '--reuid=65534', '--regid=65534', '--clear-groups',
                               'bash', str(ROOT / 'install.sh'), 'native', '--dolphin-only', *args],
                              env=self.env, capture_output=True, text=True, timeout=25)

    def test_missing_components_install_via_mock_apt_then_only_dolphin_is_deployed(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = [json.loads(line) for line in (self.home / 'apt-calls').read_text().splitlines()]
        self.assertEqual(calls[0], ['apt-get', 'update'])
        self.assertIn('--no-install-recommends', calls[1])
        self.assertIn('kio-extras', calls[1])
        self.assertIn('udisks2', calls[1])
        self.assertNotIn('Hyprland', calls[1])
        self.assertNotIn('sddm', calls[1])
        self.assertEqual(read_ini(self.home / '.config/dolphinrc').sections(), ['UiSettings'])
        self.assertTrue((self.home / '.config/Kvantum/Frosted-Glass-Dolphin/Frosted-Glass-Dolphin.svg').is_file())
        self.assertFalse((self.home / '.config/hypr').exists())
        backups = list((self.home / '.local/state/hyprixe/backups').iterdir())
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len((self.home / 'apt-calls').read_text().splitlines()), 2)
        self.assertEqual(list((self.home / '.local/state/hyprixe/backups').iterdir()), backups)

    def test_failed_component_apt_does_not_write_configuration(self):
        self.env['MOCK_APT_FAILURE'] = '1'
        result = self.run_installer()
        self.assertEqual(result.returncode, 17, result.stdout + result.stderr)
        self.assertFalse((self.home / '.config').exists())
        self.assertFalse((self.home / '.local').exists())

    def test_no_packages_fails_before_any_write_when_component_is_missing(self):
        result = self.run_installer('--no-packages')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing preview dependency', result.stderr)
        self.assertFalse((self.home / 'apt-calls').exists())
        self.assertFalse((self.home / '.config').exists())


if __name__ == '__main__':
    unittest.main()
