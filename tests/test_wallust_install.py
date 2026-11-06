"""Debian pinning, archive integrity, idempotence and pre-mutation preflight."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from support import ROOT
import wallust


class WallustInstallTests(unittest.TestCase):
    PLATFORM = 'debian'

    def test_exact_stable_version_and_hash_are_pinned(self):
        self.assertEqual(wallust.VERSION, '3.5.1')
        self.assertEqual(wallust.SHA256, '45afe16bc8c14dab61ff2acf885034664a6b917ca2ea874ff24eb5107d311ecc')
        self.assertNotIn('master', wallust.URL)
        self.assertIn('--locked', (ROOT / 'profiles/debian/install/wallust.py').read_text())

    def test_other_major_or_minor_versions_are_not_silently_accepted(self):
        for output, expected in (('wallust 3.5.1 (release)', True), ('wallust 2.10.0', False),
                                 ('wallust 4.0.0', False), ('wallust 3.5.0', False),
                                 ('wallust 3.5.1-alpha', False)):
            with self.subTest(output=output), patch.object(wallust.shutil, 'which', return_value='/bin/wallust'), \
                 patch.object(wallust.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output, '')):
                self.assertEqual(wallust.compatible(), expected)

    def test_compatible_installation_performs_no_download_or_build(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(wallust, 'compatible', return_value=True), \
             patch.object(wallust.urllib.request, 'urlopen') as download, patch.object(wallust.subprocess, 'run') as build:
            wallust.stage(Path(folder))
            download.assert_not_called(); build.assert_not_called()
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_bad_release_hash_is_rejected_before_extracting_or_building(self):
        response = Mock(); response.read.return_value = b'corrupted release'
        response.__enter__ = Mock(return_value=response); response.__exit__ = Mock(return_value=False)
        with tempfile.TemporaryDirectory() as folder, patch.object(wallust, 'compatible', return_value=False), \
             patch.object(wallust.urllib.request, 'urlopen', return_value=response), \
             patch.object(wallust.subprocess, 'run') as build:
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'): wallust.stage(Path(folder))
            build.assert_not_called()
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_no_packages_rejects_wrong_wallust_before_any_home_modification(self):
        if os.geteuid() == 0 and not shutil.which('runuser'):
            self.skipTest('needs a desktop user or runuser for the installer root guard')
        with tempfile.TemporaryDirectory(prefix='hyprixe-preflight-') as folder:
            root = Path(folder); root.chmod(0o755)
            home = root / 'home'; home.mkdir(mode=0o777); home.chmod(0o777)
            binaries = root / 'bin'; binaries.mkdir()
            binary = binaries / 'wallust'; binary.write_text('#!/bin/sh\necho wallust 2.10.0\n'); binary.chmod(0o755)
            command = ['env', 'HOME=' + str(home), 'PATH=' + str(binaries) + ':/usr/bin:/bin',
                       'bash', str(ROOT / 'install.sh'), 'native', '--no-packages']
            if os.geteuid() == 0:
                command = ['runuser', '-u', 'nobody', '--', *command]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Wallust 3.5.1 required', result.stderr)
            self.assertEqual(list(home.iterdir()), [])
