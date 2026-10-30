"""Account changes are mocks; native Zsh optionally uses verified staged upstream."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import deploy
import interactive_shell as shell
import shell_assets as assets


class AssetTests(unittest.TestCase):
    def tree(self, folder):
        pin = f'uname_s_glob="linux"; uname_m_glob="{assets.machine()}"; file="gitstatusd-linux-${{uname_m}}"; version="v1.5.4"; sha256="' + 'a' * 64 + '";'
        files = {'powerlevel10k.zsh-theme': b'# upstream fixture', 'internal/p10k.zsh': b'# core fixture',
                 'LICENSE': b'license', 'gitstatus/install.info': pin.encode(),
                 'gitstatus/usrbin/gitstatusd-linux-' + assets.machine(): b'prebuilt fixture'}
        for name, data in files.items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o755 if 'usrbin/' in name else 0o644)
        (folder / assets.STAMP).write_text(json.dumps(assets.tree_manifest(folder)))

    def test_corrupt_checksum_is_rejected_before_caching(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(assets.urllib.request, 'urlopen', return_value=io.BytesIO(b'wrong')):
            cache = Path(tmp) / 'cache'
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                assets.download({'url': 'https://example.invalid/pinned', 'sha256': 'a' * 64}, cache)
            self.assertFalse(cache.exists())

    def test_archive_traversal_and_links_are_rejected_before_extraction(self):
        for name, kind in (('../outside', tarfile.REGTYPE), ('root/link', tarfile.SYMTYPE)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                data = io.BytesIO()
                with tarfile.open(fileobj=data, mode='w:gz') as archive:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = '/etc/passwd' if kind == tarfile.SYMTYPE else ''
                    archive.addfile(member)
                target = Path(tmp) / 'export'
                with self.assertRaises(ValueError):
                    assets.extract(data.getvalue(), target)
                self.assertFalse(target.exists())

    def test_verified_install_reused_offline_without_network_or_generated_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            data = home / 'data with spaces'
            tree = data / 'hyprixe/powerlevel10k'
            self.tree(tree)
            (tree / 'local-generated.zwc').write_bytes(b'cache must not enter payload')
            pins = dict(assets.PINS, symbols={'sha256': assets.sha(b'font')}, symbols_license={'sha256': assets.sha(b'license')})
            fonts = data / 'fonts/hyprixe-symbols'
            fonts.mkdir(parents=True)
            (fonts / assets.FONT).write_bytes(b'font')
            (fonts / 'LICENSE').write_bytes(b'license')
            with patch.object(assets, 'PINS', pins), patch.object(assets, 'check_daemon'), \
                 patch.object(assets, 'download', side_effect=AssertionError('network used')):
                assets.prepare(home / 'stage', home, data, offline=True)
                assets.validate(home / 'stage/powerlevel10k')
                self.assertFalse((home / 'stage/powerlevel10k/local-generated.zwc').exists())
                self.assertIn(data / 'hyprixe/powerlevel10k/powerlevel10k.zsh-theme', assets.payload(home, data, home / 'stage'))
            (tree / 'internal/p10k.zsh').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'missing/changed'):
                assets.validate(tree)

    def test_offline_missing_asset_reports_actionable_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'without --no-packages'):
                assets.download({'sha256': 'a' * 64}, Path(tmp), offline=True)


class ShellTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe shell transaction ')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.roots = {key: self.home / name for key, name in (('config', 'settings with spaces'), ('data', 'data'), ('state', 'state'))}
        self.current = '/bin/bash'
        self.events = []
        self.fail_change = False
        self.after_change_failure = False
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, HOME=str(self.home)))
        self.stack.enter_context(patch.object(shell.os, 'getuid', return_value=1000))
        self.stack.enter_context(patch.object(shell.pwd, 'getpwuid', side_effect=lambda uid: self.user()))
        self.stack.enter_context(patch.object(shell, 'dependencies', return_value=[]))
        self.stack.enter_context(patch.object(shell, 'allowed_shell', return_value=True))
        self.stack.enter_context(patch.object(shell.shutil, 'which', side_effect=lambda name, **kwargs: '/usr/bin/' + name))
        self.stack.enter_context(patch.object(shell, 'startup', side_effect=lambda *args: self.events.append('startup')))
        self.stack.enter_context(patch.object(shell, 'font_ready'))
        self.stack.enter_context(patch.object(assets, 'validate', return_value={}))
        self.stack.enter_context(patch.object(assets, 'check_daemon'))
        self.stack.enter_context(patch.object(shell.subprocess, 'run', side_effect=self.runner))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        for name in ('.zshrc', '.p10k.zsh'):
            (self.home / name).write_text('old personal ' + name)
            (self.home / name).chmod(0o640)

    def user(self):
        return SimpleNamespace(pw_uid=1000, pw_name='desktop-fixture', pw_dir=str(self.home), pw_shell=self.current)

    def runner(self, args, **kwargs):
        if args[0] == 'fc-cache':
            self.events.append('font-cache')
        elif args[:2] == ['sudo', '/usr/bin/chsh']:
            self.assertEqual(args[-1], 'desktop-fixture')
            self.events.append('chsh:' + args[3])
            if self.fail_change and args[3] == '/usr/bin/zsh':
                if self.after_change_failure:
                    self.current = args[3]
                raise subprocess.CalledProcessError(1, args)
            self.current = args[3]
        else:
            self.fail('Unexpected subprocess: ' + str(args))
        return subprocess.CompletedProcess(args, 0)

    def install(self):
        return deploy.install_with_shell(self.home, self.roots, 'native', sddm=False)

    def test_install_repeat_restore_preserve_dotfiles_modes_and_account(self):
        backup = self.install()
        self.assertEqual(self.current, '/usr/bin/zsh')
        self.assertLess(self.events.index('startup'), self.events.index('chsh:/usr/bin/zsh'))
        self.assertEqual((self.home / '.zshrc').read_bytes(), (ROOT / '.zshrc').read_bytes())
        self.assertIsNone(self.install())
        self.assertEqual(self.events.count('chsh:/usr/bin/zsh'), 1)
        self.assertEqual(len(list((self.roots['state'] / 'hyprixe/backups').iterdir())), 1)
        deploy.restore(backup, self.home)
        self.assertEqual(self.current, '/bin/bash')
        for name in ('.zshrc', '.p10k.zsh'):
            self.assertEqual((self.home / name).read_text(), 'old personal ' + name)
            self.assertEqual((self.home / name).stat().st_mode & 0o777, 0o640)

    def test_startup_failure_rolls_back_without_changing_shell(self):
        with patch.object(shell, 'startup', side_effect=ValueError('broken plugin')):
            with self.assertRaisesRegex(ValueError, 'broken plugin'):
                self.install()
        self.assertEqual(self.current, '/bin/bash')
        self.assertFalse(any(x.startswith('chsh:') for x in self.events))
        self.assertEqual((self.home / '.zshrc').read_text(), 'old personal .zshrc')

    def test_chsh_error_before_or_after_account_change_rolls_back(self):
        self.fail_change = True
        for after in (False, True):
            with self.subTest(after=after):
                self.after_change_failure = after
                with self.assertRaises(subprocess.CalledProcessError):
                    self.install()
                self.assertEqual(self.current, '/bin/bash')
                self.assertEqual((self.home / '.zshrc').read_text(), 'old personal .zshrc')

    def test_manual_shell_change_blocks_restore_before_files_are_changed(self):
        backup = self.install()
        self.current = '/usr/bin/fish'
        before = (self.home / '.zshrc').read_bytes()
        with self.assertRaisesRegex(ValueError, 'changed since installation'):
            deploy.restore(backup, self.home)
        self.assertEqual((self.home / '.zshrc').read_bytes(), before)
        self.assertEqual(self.current, '/usr/bin/fish')

    def test_restore_can_recover_bash_even_if_zsh_was_removed_externally(self):
        backup = self.install()
        with patch.object(shell, 'allowed_shell', side_effect=lambda path: path == '/bin/bash'):
            deploy.restore(backup, self.home)
        self.assertEqual(self.current, '/bin/bash')
        self.assertEqual((self.home / '.zshrc').read_text(), 'old personal .zshrc')

    def test_root_wrong_home_and_unlisted_shell_are_refused_before_install(self):
        for damaged in (dict(pw_uid=0), dict(pw_dir='/different-home')):
            user = self.user()
            for key, value in damaged.items():
                setattr(user, key, value)
            with patch.object(shell.pwd, 'getpwuid', return_value=user):
                with self.assertRaises(ValueError):
                    self.install()
        with patch.object(shell, 'allowed_shell', return_value=False):
            with self.assertRaisesRegex(ValueError, '/etc/shells'):
                self.install()
        self.assertFalse((self.roots['state'] / 'hyprixe/backups').exists())


STAGE = os.environ.get('HYPRIXE_TEST_SHELL_STAGE')


@unittest.skipUnless(STAGE and shutil.which('zsh'), 'verified upstream shell staging required for native startup tests')
class NativeZshTests(unittest.TestCase):
    def test_real_login_interactive_startup_and_noninteractive_isolation(self):
        with tempfile.TemporaryDirectory(prefix='hyprixe native zsh ') as tmp:
            home = Path(tmp)
            roots = {key: home / name for key, name in (('config', 'config'), ('data', 'data with spaces'), ('state', 'state'))}
            content = assets.payload(home, roots['data'], Path(STAGE))
            for name in ('.zshrc', '.p10k.zsh'):
                content[home / name] = ((ROOT / name).read_bytes(), 0o644)
            # Test-only exclusion of Docker Desktop's dangling WSL completion link.
            docker = Path('/usr/share/zsh/vendor-completions/_docker')
            if docker.is_symlink() and not docker.exists():
                (home / '.zshenv').write_text('fpath=("${(@)fpath:#/usr/share/zsh/vendor-completions}")\n')
            with patch.dict(os.environ, HOME=str(home)), contextlib.redirect_stdout(io.StringIO()):
                deploy.install(home, roots, 'native', custom_files=content)
                shell.startup(home, roots)
                result = subprocess.run(['zsh', '-c', '(( ! $+functions[p10k] )) && print NONINTERACTIVE_OK'],
                                        capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'NONINTERACTIVE_OK')
