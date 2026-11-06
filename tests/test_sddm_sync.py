"""System snapshot protocol, ownership, safe destinations and atomic publication."""
import array
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from support import ROOT, configure_imports
configure_imports()
import sddm_sync as sync
from engine import defaults


class SddmSyncTests(unittest.TestCase):
    PLATFORM = 'debian'
    def setUp(self):
        from PIL import Image
        self.temp = tempfile.TemporaryDirectory(prefix='hyprixe system sync ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / 'private image.png'
        Image.new('RGB', (12, 8), 'purple').save(self.image)
        self.image.chmod(0o600)
        self.fd = os.open(self.image, os.O_RDONLY)
        self.addCleanup(os.close, self.fd)
        self.state = self.root / 'system/theme'
        self.receiver = sync.Receiver(self.state)
        self.palette = {role: defaults(ROOT / 'common/theme')[role] for role in sync.ROLES}
        self.request = {'format': 1, 'palette': self.palette, 'image_hash': hashlib.sha256(self.image.read_bytes()).hexdigest()}

    def publish(self):
        self.receiver.receive(self.request, self.fd, os.getuid())
        return self.state / 'current'

    def test_valid_snapshot_is_public_decoded_copy_and_contains_no_home_paths(self):
        from PIL import Image
        current = self.publish()
        self.assertTrue(current.is_symlink())
        with Image.open(current / 'wallpaper.png') as image:
            self.assertEqual(image.size, (12, 8))
        for name in ('wallpaper.png', 'Palette.qml', 'palette.json', 'manifest.json'):
            self.assertEqual(stat.S_IMODE((current / name).stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(current.stat().st_mode), 0o755)
        qml = (current / 'Palette.qml').read_text()
        self.assertNotIn(str(self.image), qml)
        self.assertIn((current.resolve() / 'wallpaper.png').as_uri(), qml)
        self.assertEqual(json.loads((current / 'palette.json').read_text()), self.palette)

    def test_reject_destination_traversal_extra_options_and_qml_injection(self):
        for extra in ({'destination': '/etc/passwd'}, {'path': '../escape'}, {'options': '--evil; sh'}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.receiver.receive(dict(self.request, **extra), self.fd, os.getuid())
        bad = dict(self.palette, accent='"; Qt.quit(); //')
        with self.assertRaises(ValueError):
            self.receiver.receive(dict(self.request, palette=bad), self.fd, os.getuid())
        self.assertFalse(self.state.exists())

    def test_non_image_non_owner_hash_change_and_unsafe_outputs_refused(self):
        with self.assertRaises(ValueError):
            self.receiver.receive(self.request, self.fd, os.getuid() + 1)
        with self.assertRaises(ValueError):
            self.receiver.receive(dict(self.request, image_hash='0' * 64), self.fd, os.getuid())
        text = self.root / 'not image'
        text.write_bytes(b'not an image')
        with text.open('rb') as stream, self.assertRaises((ValueError, OSError)):
            self.receiver.receive(dict(self.request, image_hash=hashlib.sha256(text.read_bytes()).hexdigest()), stream.fileno(), os.getuid())
        self.state.parent.mkdir()
        self.state.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            self.publish()

    def test_client_rejects_missing_symlink_and_nonowned_sources_before_socket(self):
        palette = self.root / 'palette.json'
        palette.write_text(json.dumps(self.palette))
        with self.assertRaises(OSError):
            sync.client(self.root / 'missing', palette)
        link = self.root / 'unexpected-link'
        link.symlink_to(self.image)
        with self.assertRaises(OSError):
            sync.client(link, palette)
        with patch('sddm_sync.os.getuid', return_value=os.getuid() + 1), self.assertRaises(ValueError):
            sync.client(self.image, palette)

    def test_interrupted_snapshot_leaves_previous_complete_generation(self):
        current = self.publish()
        original = current.resolve()
        original_replace = os.replace
        def interrupted(source, destination):
            if Path(destination) == current:
                raise OSError('interrupted publish')
            original_replace(source, destination)
        with patch('sddm_sync.os.replace', side_effect=interrupted), self.assertRaises(OSError):
            self.publish()
        self.assertEqual(current.resolve(), original)
        self.assertEqual(len(list((self.state / 'generations').iterdir())), 1)

    def test_existing_unexpected_current_symlink_and_world_writable_state_refused(self):
        current = self.publish()
        current.unlink(); current.symlink_to('../outside')
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            self.publish()
        current.unlink(); self.state.chmod(0o777)
        with self.assertRaisesRegex(ValueError, 'exclusively'):
            self.publish()

    def test_wire_authenticates_kernel_peer_and_requires_exactly_one_descriptor(self):
        def request(authorized, fds, value=None):
            sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            self.addCleanup(sender.close); self.addCleanup(receiver.close)
            thread = threading.Thread(target=sync.handle, args=(receiver, self.receiver, authorized))
            thread.start()
            try:
                ancillary = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', fds))] if fds else []
                sender.sendmsg([json.dumps(value or self.request).encode()], ancillary)
                return json.loads(sender.recv(sync.MAX_MESSAGE))
            finally:
                thread.join(5)
                self.assertFalse(thread.is_alive())
        self.assertFalse(request(set(), [self.fd])['ok'])
        self.assertFalse(request({os.getuid()}, [])['ok'])
        self.assertFalse(request({os.getuid()}, [self.fd, self.fd])['ok'])
        self.assertTrue(request({os.getuid()}, [self.fd])['ok'])

    def test_real_client_transfers_private_image_without_any_server_source_path(self):
        endpoint = self.root / 'sync.sock'
        policy = self.root / 'palette.json'; policy.write_text(json.dumps(self.palette))
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as listener:
            listener.bind(str(endpoint)); listener.listen(1)
            def serve():
                connection, _ = listener.accept()
                with connection:
                    sync.handle(connection, self.receiver, {os.getuid()})
            thread = threading.Thread(target=serve)
            thread.start()
            try:
                with patch('sddm_sync.SOCKET', str(endpoint)):
                    sync.client(self.image, policy)
            finally:
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertTrue((self.state / 'current/wallpaper.png').is_file())

    @unittest.skipUnless(os.geteuid() == 0 and hasattr(os, 'fork'), 'isolated unprivileged receiver check')
    def test_unprivileged_receiver_can_copy_descriptor_but_cannot_read_sender_home(self):
        import pwd
        uid = pwd.getpwnam('nobody').pw_uid
        with tempfile.TemporaryDirectory(prefix='hyprixe-public-test-') as folder:
            public = Path(folder); public.chmod(0o755)
            state = public / 'theme'; state.mkdir(); os.chown(state, uid, uid)
            sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            sender.settimeout(10)
            pid = os.fork()
            if pid == 0:
                try:
                    sender.close(); os.close(self.fd)
                    os.setgroups([]); os.setgid(uid); os.setuid(uid)
                    try:
                        self.image.open('rb')
                    except PermissionError:
                        pass
                    else:
                        os._exit(2)
                    # Test root is the sender; production policy never enrolls 0.
                    sync.handle(receiver, sync.Receiver(state), {0})
                    os._exit(0)
                except BaseException:
                    os._exit(1)
            receiver.close()
            try:
                sender.sendmsg([json.dumps(self.request).encode()],
                               [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [self.fd]))])
                self.assertTrue(json.loads(sender.recv(sync.MAX_MESSAGE))['ok'])
            finally:
                sender.close()
                _, status = os.waitpid(pid, 0)
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)
            self.assertEqual((state / 'current/wallpaper.png').stat().st_uid, uid)

    def test_cli_exposes_no_destination_flags_and_root_cannot_serve(self):
        script = ROOT / 'profiles/debian/install/sddm_sync.py'
        for arguments in (['client', str(self.image), '/tmp/palette', '--destination', '../bad'], ['serve', '--root', '/tmp']):
            result = subprocess.run([sys.executable, str(script), *arguments], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
        if os.geteuid() == 0:
            with self.assertRaisesRegex(ValueError, 'never run as root'):
                sync.main(['serve'])

    @unittest.skipUnless(os.geteuid() == 0, 'root-owned authorization contract')
    def test_authorization_must_be_root_owned_regular_and_not_writable(self):
        policy = self.root / 'authorized.json'
        policy.write_text('{"format":1,"uids":[1000,1001]}')
        with patch('sddm_sync.USERS', policy):
            self.assertEqual(sync.allowed_users(), {1000, 1001})
            policy.chmod(0o666)
            with self.assertRaises(ValueError):
                sync.allowed_users()
            policy.chmod(0o644)
            policy.write_text('{"format":1,"uids":[0]}')
            with self.assertRaises(ValueError):
                sync.allowed_users()
