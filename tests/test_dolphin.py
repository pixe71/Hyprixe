import base64
import contextlib
import errno
import io
import json
import os
from pathlib import Path
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
from dolphin_config import VIEW_XATTR, show_places_groups
from dolphin_checks import check_source


class DolphinDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe Dolphin ')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'desktop user'
        self.home.mkdir()
        self.roots = {key: self.home / name for key, name in
                      (('config', 'settings with spaces'), ('data', 'application data'), ('state', 'session state'))}
        self.env = patch.dict(os.environ, {'HOME': str(self.home),
            **{'XDG_' + key.upper() + '_HOME': str(path) for key, path in self.roots.items()}})
        self.env.start()
        self.addCleanup(self.env.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def install(self, **kwargs):
        return deploy.install(self.home, self.roots, 'native', dolphin_only=True, **kwargs)

    def write(self, key, name, data):
        path = self.roots[key] / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path

    def xattr(self, path, value):
        try:
            os.setxattr(path, VIEW_XATTR, value)
        except OSError as exc:
            if exc.errno in (errno.ENOTSUP, errno.EOPNOTSUPP):
                self.skipTest('Filesystem does not support view-property xattrs')
            raise

    def test_dolphin_only_installs_defaults_without_touching_desktop_or_profile(self):
        files = [self.write('config', 'hypr/hyprland.lua', 'personal Hyprland'),
                 self.write('config', 'hypr/profile.lua', 'current profile'),
                 self.write('config', 'kdeglobals', 'current Qt settings')]
        backup = self.install()
        manifest = deploy.read_manifest(backup)
        self.assertEqual(manifest['scope'], 'dolphin')
        self.assertEqual(len(manifest['files']), 5)
        self.assertEqual([p.read_text() for p in files], ['personal Hyprland', 'current profile', 'current Qt settings'])
        self.assertTrue((self.roots['data'] / 'dolphin/view_properties/global/.directory').is_file())
        state = (self.roots['state'] / 'dolphinstaterc').read_text()
        self.assertIn('State=AAAA', state)
        self.assertNotIn(str(self.home), state)
        self.assertNotIn('screen:', state)
        self.assertIsNone(self.install(), 'Repeat must be a no-op before the application changes its state')

    def test_preserves_existing_geometry_and_unrelated_information_preferences(self):
        state = self.write('state', 'dolphinstaterc', '[State]\nState=old\n1920x1080 screen: Width=1234\n[Other]\nvalue=keep\n')
        info = self.write('config', 'baloofileinformationrc', '[Show]\ncustomProperty=true\nrating=true\n[Other]\nvalue=keep\n[Misc]\nversion=42\n')
        backup = self.install()
        self.assertIn('Width=1234', state.read_text())
        self.assertIn('value=keep', state.read_text())
        self.assertIn('customProperty=true', info.read_text())
        self.assertIn('rating=false', info.read_text())
        self.assertIn('version=42', info.read_text())
        deploy.restore(backup, self.home)
        self.assertIn('State=old', state.read_text())
        self.assertIn('rating=true', info.read_text())

    def test_existing_places_groups_are_unhidden_without_losing_bookmarks(self):
        places = self.write('data', 'user-places.xbel', '''<?xml version="1.0"?><!DOCTYPE xbel>
<xbel><info><metadata owner="http://www.kde.org"><GroupState-Devices-IsHidden>true</GroupState-Devices-IsHidden>
<GroupState-Remote-IsHidden>true</GroupState-Remote-IsHidden></metadata></info>
<bookmark href="file:///personal-folder"><title>Personal bookmark</title></bookmark></xbel>''')
        original = places.read_bytes()
        backup = self.install()
        root = ET.fromstring(places.read_bytes())
        self.assertEqual(root.find('bookmark').get('href'), 'file:///personal-folder')
        self.assertEqual(root.findtext('info/metadata/GroupState-Devices-IsHidden'), 'false')
        self.assertEqual(root.findtext('info/metadata/GroupState-Remote-IsHidden'), 'true')
        self.assertEqual(show_places_groups(places.read_bytes()), places.read_bytes())
        deploy.restore(backup, self.home)
        self.assertEqual(places.read_bytes(), original)

    def test_invalid_places_abort_before_any_configuration_write(self):
        places = self.write('data', 'user-places.xbel', '<broken')
        with self.assertRaisesRegex(ValueError, 'Cannot read user-places'):
            self.install()
        self.assertEqual(places.read_text(), '<broken')
        self.assertFalse(self.roots['config'].exists())
        self.assertFalse(self.roots['state'].exists())

    def test_dry_run_does_not_create_configs_or_backups(self):
        self.install(dry=True)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_baloo_omitted_true_defaults_are_accepted_after_real_app_saves(self):
        from dolphin_checks import check_installed
        self.install()
        for name in ('Kvantum', 'qt6ct'):
            shutil.copytree(ROOT / '.config' / name, self.roots['config'] / name)
        shutil.copyfile(ROOT / '.config/kdeglobals', self.roots['config'] / 'kdeglobals')
        self.write('config', 'baloofileinformationrc', '[Misc]\nversion=13\n[Show]\ntags=false\nrating=false\nuserComment=false\n')
        results = []
        check_installed(lambda ok, label: results.append((ok, label)))
        self.assertTrue(all(ok for ok, _ in results), results)

    def test_native_view_defaults_survive_directory_to_xattr_migration(self):
        from dolphin_checks import check_installed
        self.install()
        for name in ('Kvantum', 'qt6ct'):
            shutil.copytree(ROOT / '.config' / name, self.roots['config'] / name)
        shutil.copyfile(ROOT / '.config/kdeglobals', self.roots['config'] / 'kdeglobals')
        directory = self.roots['data'] / 'dolphin/view_properties/global'
        (directory / '.directory').unlink()
        for value in (None, b'[Dolphin]\nVersion=4\nVisibleRoles=Icons_text\n'):
            if value:
                self.xattr(directory, value)
            results = []
            check_installed(lambda ok, label: results.append((ok, label)))
            self.assertTrue(all(ok for ok, _ in results), results)
        self.xattr(directory, b'[Dolphin]\nVersion=4\nViewMode=1\n')
        results = []
        check_installed(lambda ok, label: results.append((ok, label)))
        self.assertTrue(any(not ok for ok, _ in results), 'A real Details-mode override must still fail')

    def test_restore_can_save_dolphin_runtime_edits_before_restoring_originals(self):
        config = self.write('config', 'dolphinrc', '[General]\nOriginal=true\n')
        personal = self.write('data', 'personal.txt', 'not managed')
        backup = self.install()
        config.write_text(config.read_text() + '\n[Runtime]\nChanged=true\n')
        current = config.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Nothing restored'):
            deploy.restore(backup, self.home)
        deploy.restore(backup, self.home, save_dolphin_changes=True)
        self.assertEqual(config.read_text(), '[General]\nOriginal=true\n')
        self.assertEqual(personal.read_text(), 'not managed')
        saved = next(backup.glob('preserved-dolphin-*'))
        records = json.loads((saved / 'manifest.json').read_text())['files']
        entry = next(e for e in records if e['path'] == str(config))
        self.assertEqual((saved / entry['saved']).read_bytes(), current)

    def test_restore_accounts_for_native_migration_to_directory_xattr(self):
        directory = self.roots['data'] / 'dolphin/view_properties/global'
        directory.mkdir(parents=True)
        self.xattr(directory, b'original view preferences')
        os.setxattr(directory, 'user.hyprixe-test-unrelated', b'keep')
        backup = self.install()
        props = directory / '.directory'
        after = props.read_bytes()
        self.xattr(directory, after)
        props.unlink()  # Native Dolphin migration removes the legacy file.
        with self.assertRaisesRegex(ValueError, 'Nothing restored'):
            deploy.restore(backup, self.home)
        deploy.restore(backup, self.home, save_dolphin_changes=True)
        self.assertEqual(os.getxattr(directory, VIEW_XATTR), b'original view preferences')
        self.assertEqual(os.getxattr(directory, 'user.hyprixe-test-unrelated'), b'keep')
        self.assertFalse(props.exists())
        saved = next(backup.glob('preserved-dolphin-*'))
        metadata = json.loads((saved / 'manifest.json').read_text())['view_xattr']
        self.assertEqual(base64.b64decode(metadata['value']), after)

    def test_fresh_install_restore_removes_only_new_view_metadata(self):
        backup = self.install()
        directory = self.roots['data'] / 'dolphin/view_properties/global'
        self.xattr(directory, b'view preferences written by Dolphin')
        deploy.restore(backup, self.home, save_dolphin_changes=True)
        self.assertFalse((directory / '.directory').exists())
        if directory.exists():
            with self.assertRaises(OSError):
                os.getxattr(directory, VIEW_XATTR)

    def test_restore_recreates_an_original_attribute_only_directory_if_removed(self):
        directory = self.roots['data'] / 'dolphin/view_properties/global'
        directory.mkdir(parents=True)
        self.xattr(directory, b'original attribute-only preferences')
        backup = self.install()
        (directory / '.directory').unlink()
        directory.rmdir()
        deploy.restore(backup, self.home, save_dolphin_changes=True)
        self.assertEqual(os.getxattr(directory, VIEW_XATTR), b'original attribute-only preferences')

    def test_save_dolphin_changes_never_allows_unrelated_conflicts(self):
        backup = deploy.install(self.home, self.roots, 'native')
        unrelated = self.roots['config'] / 'hypr/hyprland.lua'
        unrelated.write_text('personal edit')
        config = self.roots['config'] / 'dolphinrc'
        config.write_text('changed Dolphin settings')
        with self.assertRaisesRegex(ValueError, 'Nothing restored'):
            deploy.restore(backup, self.home, save_dolphin_changes=True)
        self.assertEqual(unrelated.read_text(), 'personal edit')
        self.assertEqual(config.read_text(), 'changed Dolphin settings')
        self.assertEqual(list(backup.glob('preserved-dolphin-*')), [])

    def test_unrelated_transaction_does_not_own_or_restore_dolphin_metadata(self):
        deploy.install(self.home, self.roots, 'native')
        hypr = self.roots['config'] / 'hypr/hyprland.lua'
        hypr.write_text('before unrelated update')
        backup = deploy.install(self.home, self.roots, 'native')
        manifest = deploy.read_manifest(backup)
        self.assertEqual(manifest['dolphin_targets'], [])
        self.assertNotIn('dolphin_view_xattr', manifest)
        directory = self.roots['data'] / 'dolphin/view_properties/global'
        self.xattr(directory, b'new personal view preferences')
        deploy.restore(backup, self.home)
        self.assertEqual(hypr.read_text(), 'before unrelated update')
        self.assertEqual(os.getxattr(directory, VIEW_XATTR), b'new personal view preferences')

    def test_restore_preview_does_not_copy_or_modify_runtime_changes(self):
        backup = self.install()
        config = self.roots['config'] / 'dolphinrc'
        config.write_text('runtime changed')
        deploy.restore(backup, self.home, dry=True, save_dolphin_changes=True)
        self.assertEqual(config.read_text(), 'runtime changed')
        self.assertEqual(list(backup.glob('preserved-dolphin-*')), [])


class DolphinChecksTests(unittest.TestCase):
    def test_component_dependencies_are_also_in_full_install_manifest(self):
        def packages(path):
            return {line.split('#', 1)[0].strip() for line in path.read_text().splitlines()} - {''}
        component = packages(ROOT / 'packages-dolphin.txt')
        self.assertTrue({'dolphin', 'kio-extras', 'udisks2', 'qt6-style-kvantum'} <= component)
        self.assertTrue(component <= packages(ROOT / 'packages.txt'))

    def test_kconfig_geometry_keys_with_colons_remain_distinct(self):
        from dolphin_config import read_ini
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / 'dolphinstaterc'
            state.write_text('[State]\n1920x1080 screen: Width=1280\n1920x1080 screen: Height=800\n')
            parsed = read_ini(state)
            self.assertEqual(parsed['State']['1920x1080 screen: Width'], '1280')
            self.assertEqual(parsed['State']['1920x1080 screen: Height'], '800')

    def test_source_contract(self):
        results = []
        check_source(lambda ok, label: results.append((ok, label)), ROOT)
        self.assertTrue(all(ok for ok, _ in results), results)

    def test_missing_source_files_report_failures_without_traceback(self):
        results = []
        with tempfile.TemporaryDirectory() as temp:
            check_source(lambda ok, label: results.append((ok, label)), Path(temp))
        self.assertEqual(len(results), 5)
        self.assertFalse(any(ok for ok, _ in results))

    def test_running_dolphin_is_refused_without_killing_it(self):
        from dolphin_config import ensure_closed
        with patch('dolphin_config.shutil.which', return_value='/bin/pgrep'), \
             patch('dolphin_config.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as run:
            with self.assertRaisesRegex(ValueError, 'Close all Dolphin'):
                ensure_closed()
        self.assertEqual(run.call_args.args[0], ['pgrep', '-u', str(os.getuid()), '-x', 'dolphin'])

    @unittest.skipUnless(subprocess.run([sys.executable, '-c', 'import PyQt6.QtWidgets'], capture_output=True).returncode == 0,
                         'optional python3-pyqt6 needed for real Qt dock-state restore')
    def test_real_qt_restores_right_stacked_docks_at_multiple_window_sizes(self):
        code = '''import sys,json
from PyQt6.QtCore import Qt,QByteArray
from PyQt6.QtWidgets import QApplication,QMainWindow,QDockWidget,QToolBar,QWidget
app=QApplication([]); state=QByteArray.fromBase64(sys.argv[1].encode())
for width,height in [(1280,800),(1100,680),(960,640)]:
 w=QMainWindow(); w.setCentralWidget(QWidget()); bar=QToolBar(); bar.setObjectName('mainToolBar');w.addToolBar(bar)
 docks={}
 for name in ('placesDock','infoDock','foldersDock','terminalDock'):
  d=QDockWidget();d.setObjectName(name);d.setWidget(QWidget());w.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,d);docks[name]=d
 w.resize(width,height);w.show();assert w.restoreState(state);app.processEvents()
 p,i=docks['placesDock'],docks['infoDock']
 assert p.isVisible() and i.isVisible()
 assert w.dockWidgetArea(p)==Qt.DockWidgetArea.RightDockWidgetArea and w.dockWidgetArea(i)==Qt.DockWidgetArea.RightDockWidgetArea
 assert p.geometry().x()==i.geometry().x() and p.geometry().bottom()<i.geometry().top()
 assert not docks['foldersDock'].isVisible() and not docks['terminalDock'].isVisible()
 assert p.width()<width/3, (width,p.width())
 w.close()
print('Three native Qt dock restores passed')
'''
        from dolphin_config import read_ini
        state = read_ini(ROOT / 'dolphin/dock-layout.ini')['State']['State']
        result = subprocess.run([sys.executable, '-c', code, state], capture_output=True, text=True,
                                env=dict(os.environ, QT_QPA_PLATFORM='offscreen'), timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


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
        self.assertTrue((self.home / '.config/dolphinrc').is_file())
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
