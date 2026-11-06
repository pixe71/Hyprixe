#!/usr/bin/python3
"""Bounded SDDM snapshot receiver; runs as hyprixe-theme, never as root.

The wire protocol carries one already-open image descriptor and seven colours.
It carries no filesystem source/destination paths or commands.
"""
import argparse
import array
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import struct
import sys
import uuid
import warnings

SOCKET = '/run/hyprixe-sddm-sync.sock'
STATE = Path('/var/lib/hyprixe/theme')
USERS = Path('/etc/hyprixe/sddm-sync-users.json')
ROLES = ('background', 'surface', 'foreground', 'accent', 'accent_alt', 'border', 'error')
MAX_IMAGE = 32 * 1024 * 1024
MAX_MESSAGE = 2048


def palette_valid(palette):
    if (not isinstance(palette, dict) or set(palette) != set(ROLES) or
            any(not isinstance(v, str) or not re.fullmatch('#[0-9a-f]{6}', v) for v in palette.values())):
        raise ValueError('Expected seven semantic #rrggbb colours')
    # A broken/hostile export must not make the login text unreadable.
    def luminance(colour):
        values = [int(colour[i:i+2], 16) / 255 for i in (1, 3, 5)]
        return sum(w * (v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4)
                   for w, v in zip((.2126, .7152, .0722), values))
    for background in ('background', 'surface'):
        low, high = sorted((luminance(palette[background]), luminance(palette['foreground'])))
        if (high + .05) / (low + .05) < 4.5:
            raise ValueError('Unreadable SDDM palette')
    return palette


def encode_image(fd, uid, digest):
    from PIL import Image
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_uid != uid or not 0 < before.st_size <= MAX_IMAGE:
        raise ValueError('Image must be a bounded regular file owned by the sending user')
    # pread does not depend on the sender-controlled shared descriptor offset.
    data = os.pread(fd, MAX_IMAGE + 1, 0)
    after = os.fstat(fd)
    if (len(data) != before.st_size or hashlib.sha256(data).hexdigest() != digest or
            (before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
            (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
        raise ValueError('Image changed during transfer')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > 36_000_000 or image.format not in ('JPEG', 'PNG', 'WEBP', 'BMP'):
                    raise ValueError('Unsupported or oversized login image (36 megapixels maximum)')
                image.load()
                output = io.BytesIO()
                # Strip metadata/extra frames and publish a decoded, safe PNG copy.
                image.convert('RGB').save(output, format='PNG')
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('Cannot decode login image: ' + str(exc)) from exc
    return output.getvalue()


def write_file(path, data):
    with path.open('xb') as stream:
        os.fchmod(stream.fileno(), 0o644)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def palette_qml(palette, image_url):
    # Only validated hex strings and a receiver-generated system URL enter QML.
    fields = ''.join(f'    readonly property string {role}: {json.dumps(palette[role])}\n' for role in ROLES)
    return ('import QtQuick\nQtObject {\n    readonly property int schema: 1\n'
            f'    readonly property string wallpaper: {json.dumps(image_url)}\n' + fields + '}\n').encode()


class Receiver:
    def __init__(self, state=STATE):
        self.state = Path(state)

    def guard(self):
        for parent in (self.state, *self.state.parents):
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise ValueError('Unsafe system theme directory')
        self.state.mkdir(parents=True, exist_ok=True, mode=0o755)
        if self.state.stat().st_uid != os.getuid() or self.state.stat().st_mode & 0o022:
            raise ValueError('System theme directory must be owned exclusively by receiver')
        self.state.chmod(0o755)
        generations = self.state / 'generations'
        if generations.is_symlink():
            raise ValueError('Unexpected generation symlink')
        generations.mkdir(exist_ok=True, mode=0o755)
        if generations.stat().st_uid != os.getuid() or generations.stat().st_mode & 0o022:
            raise ValueError('Unsafe generations directory')
        generations.chmod(0o755)
        current = self.state / 'current'
        if current.exists() or current.is_symlink():
            if (not current.is_symlink() or current.lstat().st_uid != os.getuid() or
                    not re.fullmatch('generations/[0-9a-f]{32}', os.readlink(current))):
                raise ValueError('Unexpected system current path')

    def receive(self, request, fd, uid):
        if (not isinstance(request, dict) or set(request) != {'format', 'palette', 'image_hash'} or
                request['format'] != 1 or not isinstance(request['image_hash'], str) or
                not re.fullmatch('[0-9a-f]{64}', request['image_hash'])):
            raise ValueError('Invalid sync request; paths, destinations and options are not accepted')
        palette = palette_valid(request['palette'])
        image = encode_image(fd, uid, request['image_hash'])
        self.guard()
        name = uuid.uuid4().hex
        generation = self.state / 'generations' / name
        generation.mkdir(mode=0o755)
        generation.chmod(0o755)
        temporary = self.state / ('.current-' + name)
        try:
            write_file(generation / 'wallpaper.png', image)
            write_file(generation / 'palette.json', (json.dumps(palette, sort_keys=True) + '\n').encode())
            write_file(generation / 'Palette.qml', palette_qml(palette, (generation / 'wallpaper.png').as_uri()))
            metadata = {'format': 1, 'uid': uid, 'source_hash': request['image_hash'],
                        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in generation.iterdir()}}
            write_file(generation / 'manifest.json', (json.dumps(metadata, sort_keys=True) + '\n').encode())
            with_directory = os.open(generation, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(with_directory)
            finally:
                os.close(with_directory)
            temporary.symlink_to('generations/' + name, target_is_directory=True)
            os.replace(temporary, self.state / 'current')
            directory_fd = os.open(self.state, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            if (self.state / 'current').resolve() != generation:
                shutil.rmtree(generation)
            raise
        finally:
            temporary.unlink(missing_ok=True)
        # Bound disk use; keep several complete predecessors for live greeters.
        stale = sorted((p for p in (self.state / 'generations').iterdir()
                        if re.fullmatch('[0-9a-f]{32}', p.name) and p != generation and not p.is_symlink()),
                       key=lambda p: p.stat().st_mtime_ns, reverse=True)
        for old in stale[2:]:
            shutil.rmtree(old)


def allowed_users():
    info = USERS.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('Unsafe root-owned sync authorization')
    value = json.loads(USERS.read_text())
    if (set(value) != {'format', 'uids'} or value['format'] != 1 or
            not isinstance(value['uids'], list) or any(type(uid) is not int or uid <= 0 for uid in value['uids'])):
        raise ValueError('Invalid sync authorization')
    return set(value['uids'])


def handle(connection, receiver, authorized):
    descriptors = []
    try:
        connection.settimeout(5)
        _, uid, _ = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')))
        if uid not in authorized:
            raise ValueError('User is not enrolled by the Hyprixe system installer')
        data, ancillary, flags, _ = connection.recvmsg(MAX_MESSAGE, socket.CMSG_SPACE(16 * array.array('i').itemsize), socket.MSG_CMSG_CLOEXEC)
        for level, kind, payload in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                values = array.array('i')
                values.frombytes(payload[:len(payload) - len(payload) % values.itemsize])
                descriptors.extend(values)
        if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) or len(descriptors) != 1:
            raise ValueError('Expected exactly one bounded image descriptor')
        receiver.receive(json.loads(data), descriptors[0], uid)
        connection.sendall(b'{"ok":true}')
    except (ValueError, OSError, SyntaxError, UnicodeError) as exc:
        connection.sendall(json.dumps({'ok': False, 'error': str(exc)[:256]}).encode())
    finally:
        for fd in descriptors:
            os.close(fd)


def client(image, palette_path):
    # Do not follow a supplied symlink. Core passes the already-validated real
    # image path, rather than its presentation symlink.
    fd = os.open(image, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or not 0 < info.st_size <= MAX_IMAGE:
            raise ValueError('Login wallpaper must be a bounded regular image owned by you')
        palette = json.loads(Path(palette_path).read_text())
        palette = palette_valid({role: palette[role] for role in ROLES})
        digest = hashlib.sha256(os.pread(fd, MAX_IMAGE + 1, 0)).hexdigest()
        message = json.dumps({'format': 1, 'palette': palette, 'image_hash': digest}).encode()
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as connection:
            connection.settimeout(15)
            connection.connect(SOCKET)
            connection.sendmsg([message], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [fd]))])
            response = json.loads(connection.recv(MAX_MESSAGE))
            if response.get('ok') is not True:
                raise ValueError(response.get('error', 'Sync refused'))
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='action', required=True)
    send = commands.add_parser('client', allow_abbrev=False)
    send.add_argument('image')
    send.add_argument('palette')
    commands.add_parser('serve', allow_abbrev=False)
    args = parser.parse_args(argv)
    if args.action == 'client':
        client(args.image, args.palette)
        return
    if os.geteuid() == 0:
        raise ValueError('Receiver must never run as root')
    if os.environ.get('LISTEN_PID') != str(os.getpid()) or os.environ.get('LISTEN_FDS') != '1':
        raise ValueError('Receiver requires its systemd socket')
    with socket.socket(fileno=3) as listener:
        if listener.type != socket.SOCK_SEQPACKET or listener.getsockname() != SOCKET:
            raise ValueError('Unexpected activation socket')
        while True:
            connection, _ = listener.accept()
            with connection:
                try:
                    handle(connection, Receiver(), allowed_users())
                except (OSError, ValueError) as exc:
                    print('Sync refused: ' + str(exc), file=sys.stderr)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
